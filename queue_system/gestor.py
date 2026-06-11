from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Dict, List, Optional

from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.utils.qr import gerar_qr_code_base64

if TYPE_CHECKING:
    pass

# comnetraio: marcador no GestorFila

class GestorFila:
    def __init__(self, capacidade: int = 100, politica: str = "FIFO", persistencia: Optional[Path] = None):
        self.fila: List[Senha] = []
        self.capacidade = capacidade
        self.politica = politica.upper()
        self.lock = Lock()
        self._next_id = 1
        self._department_counters: Dict[str, int] = {}
        # contactos para notificações (não persistidos)
        self._notification_contacts: Dict[int, dict] = {}
        self.persistencia = Path(persistencia) if persistencia is not None else None
        self._carregar_estado()

    def emitir_senha(
        self,
        pessoa: Pessoa,
        departamento: str = "Geral",
        prioridade_label: str = "verde",
        ws_client_id: Optional[str] = None,
    ) -> Senha:
        with self.lock:
            if len(self.fila) >= self.capacidade:
                raise ValueError("Capacidade atingida")
            via_emissao = "digital" if pessoa.acesso_digital else "papel"
            ticket_counter = self._department_counters.get(departamento, 0) + 1
            self._department_counters[departamento] = ticket_counter
            ticket_id = f"{departamento[0].upper()}-{ticket_counter:04d}"
            qr_payload = (
                f"ticket:{ticket_id};id:{pessoa.id};nome:{pessoa.nome};"
                f"departamento:{departamento};"
                f"contacto:{pessoa.contacto or pessoa.email or pessoa.telefone or ''}"
            ) if via_emissao == "digital" else None
            qr_code_base64 = gerar_qr_code_base64(qr_payload) if qr_payload else None
            senha = Senha(
                id=self._next_id,
                hora_emissao=datetime.now(timezone.utc),
                estado="emitida",
                pessoa=pessoa,
                via_emissao=via_emissao,
                departamento=departamento,
                prioridade_label=prioridade_label,
                ticket_id=ticket_id,
                ws_client_id=ws_client_id,
                qr_payload=qr_payload,
                qr_code_base64=qr_code_base64,
            )
            self.fila.append(senha)
            self._next_id += 1
            self._salvar_estado()
            return senha

    def chamar_proximo(self, departamento: Optional[str] = None) -> Optional[Senha]:
        with self.lock:
            if departamento is not None:
                fila = [senha for senha in self.fila if senha.departamento == departamento]
                if not fila:
                    return None
                if self.politica == "LIFO":
                    proxima = fila[-1]
                elif self.politica == "PRIORIDADE":
                    sorted_por_prioridade = sorted(
                        fila,
                        key=lambda item: (-item.pessoa.prioridade, item.hora_emissao),
                    )
                    proxima = sorted_por_prioridade[0]
                else:
                    proxima = fila[0]
                self.fila.remove(proxima)
            else:
                if not self.fila:
                    return None
                if self.politica == "LIFO":
                    proxima = self.fila.pop()
                elif self.politica == "PRIORIDADE":
                    sorted_por_prioridade = sorted(
                        self.fila,
                        key=lambda item: (-item.pessoa.prioridade, item.hora_emissao),
                    )
                    proxima = sorted_por_prioridade[0]
                    self.fila.remove(proxima)
                else:
                    proxima = self.fila.pop(0)
            proxima.marcar_chamada()
            # limpar contacto temporário ao chamar
            if proxima.id in self._notification_contacts:
                del self._notification_contacts[proxima.id]
            self._salvar_estado()
            return proxima

    def posicao(self, senha_id: int, departamento: Optional[str] = None) -> int:
        with self.lock:
            fila = self.fila if departamento is None else [senha for senha in self.fila if senha.departamento == departamento]
            for indice, senha in enumerate(fila, start=1):
                if senha.id == senha_id:
                    return indice
        raise ValueError(f"Senha {senha_id} não encontrada na fila")

    def cancelar_senha(self, senha_id: int, departamento: Optional[str] = None) -> int:
        with self.lock:
            fila = self.fila if departamento is None else [senha for senha in self.fila if senha.departamento == departamento]
            for indice, senha in enumerate(fila, start=1):
                if senha.id == senha_id:
                    senha.marcar_cancelada()
                    self.fila.remove(senha)
                    if senha.id in self._notification_contacts:
                        del self._notification_contacts[senha.id]
                    self._salvar_estado()
                    return indice
        raise ValueError(f"Senha {senha_id} não encontrada na fila")

    def register_notification_contact(self, senha_id: int, contact: dict) -> None:
        """Regista um contacto temporário para notificações; não é persistido."""
        with self.lock:
            self._notification_contacts[senha_id] = contact

    def get_notification_contact(self, senha_id: int) -> Optional[dict]:
        with self.lock:
            return self._notification_contacts.get(senha_id)

    def obter_senha(self, senha_id: int) -> Optional[Senha]:
        with self.lock:
            for senha in self.fila:
                if senha.id == senha_id:
                    return senha
        return None

    def obter_senha_por_ticket_id(self, ticket_id: str) -> Optional[Senha]:
        with self.lock:
            for senha in self.fila:
                if senha.ticket_id == ticket_id:
                    return senha
        return None

    def listar_fila(self, departamento: Optional[str] = None) -> List[Senha]:
        with self.lock:
            fila = self.fila if departamento is None else [senha for senha in self.fila if senha.departamento == departamento]
            if self.politica == "PRIORIDADE":
                return sorted(
                    list(fila),
                    key=lambda item: (-item.pessoa.prioridade, item.hora_emissao),
                )
            return list(fila)

    def configurar_politica(self, politica: str) -> None:
        if politica.upper() not in {"FIFO", "LIFO", "PRIORIDADE"}:
            raise ValueError("Política inválida. Use FIFO, LIFO ou PRIORIDADE.")
        with self.lock:
            self.politica = politica.upper()
            self._salvar_estado()

    def _salvar_estado(self) -> None:
        if self.persistencia is None:
            return
        estado = {
            "capacidade": self.capacidade,
            "politica": self.politica,
            "next_id": self._next_id,
            "department_counters": self._department_counters,
            "fila": [senha.to_dict() for senha in self.fila],
        }
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=str(self.persistencia.parent), suffix=".tmp") as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(estado, temp_file, default=str, indent=2)
            temp_path.replace(self.persistencia)
        except Exception:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
            raise

    def _carregar_estado(self) -> None:
        if self.persistencia is None or not self.persistencia.exists():
            return
        try:
            texto = self.persistencia.read_text(encoding="utf-8")
            dados = json.loads(texto)
            self.capacidade = int(dados.get("capacidade", self.capacidade))
            self.politica = dados.get("politica", self.politica).upper()
            self._next_id = int(dados.get("next_id", self._next_id))
            self._department_counters = {
                str(k): int(v) for k, v in (dados.get("department_counters", {}) or {}).items()
            }
            self.fila = [Senha.from_dict(item) for item in dados.get("fila", [])]
        except (json.JSONDecodeError, ValueError, TypeError):
            self.fila = []
            self._department_counters = {}
