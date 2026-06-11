from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from queue_system.entidades.pessoa import Pessoa

# comnetraio: marcador em entidade Senha

@dataclass
class Senha:
    id: int
    hora_emissao: datetime
    estado: str
    pessoa: Pessoa
    via_emissao: str = "digital"
    departamento: str = "Geral"
    prioridade_label: str = "verde"
    ticket_id: Optional[str] = None
    ws_client_id: Optional[str] = None
    qr_payload: Optional[str] = None
    qr_code_base64: Optional[str] = None
    alerta_enviado: bool = False
    hora_chamada: Optional[datetime] = None
    hora_atendida: Optional[datetime] = None
    hora_cancelada: Optional[datetime] = None

    def marcar_chamada(self) -> None:
        if self.estado not in {"emitida"}:
            return
        self.estado = "chamada"
        self.hora_chamada = datetime.now()

    def marcar_atendida(self) -> None:
        if self.estado not in {"emitida", "chamada"}:
            return
        self.estado = "atendida"
        self.hora_atendida = datetime.now()

    def marcar_cancelada(self) -> None:
        if self.estado == "cancelada":
            return
        self.estado = "cancelada"
        self.hora_cancelada = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hora_emissao": self.hora_emissao.isoformat(),
            "estado": self.estado,
            "via_emissao": self.via_emissao,
            "departamento": self.departamento,
            "prioridade_label": self.prioridade_label,
            "ticket_id": self.ticket_id,
            "ws_client_id": self.ws_client_id,
            "qr_payload": self.qr_payload,
            "qr_code_base64": self.qr_code_base64,
            "alerta_enviado": self.alerta_enviado,
            "pessoa": {
                "id": self.pessoa.id,
                "nome": self.pessoa.nome,
                "contacto": self.pessoa.contacto,
                "email": self.pessoa.email,
                "telefone": self.pessoa.telefone,
                "prioridade": self.pessoa.prioridade,
                "acesso_digital": self.pessoa.acesso_digital,
            },
            "hora_chamada": self.hora_chamada.isoformat() if self.hora_chamada else None,
            "hora_atendida": self.hora_atendida.isoformat() if self.hora_atendida else None,
            "hora_cancelada": self.hora_cancelada.isoformat() if self.hora_cancelada else None,
        }

    @staticmethod
    def from_dict(dados: dict) -> Senha:
        pessoa = Pessoa(
            id=int(dados["pessoa"]["id"]),
            nome=str(dados["pessoa"]["nome"]),
            contacto=dados["pessoa"].get("contacto"),
            email=dados["pessoa"].get("email"),
            telefone=dados["pessoa"].get("telefone"),
            prioridade=int(dados["pessoa"].get("prioridade", 0)),
            acesso_digital=bool(dados["pessoa"].get("acesso_digital", True)),
        )
        senha = Senha(
            id=int(dados["id"]),
            hora_emissao=datetime.fromisoformat(dados["hora_emissao"]),
            estado=str(dados["estado"]),
            pessoa=pessoa,
            via_emissao=str(dados.get("via_emissao", "digital")),
            departamento=str(dados.get("departamento", "Geral")),
            prioridade_label=str(dados.get("prioridade_label", "verde")),
            ticket_id=dados.get("ticket_id"),
            ws_client_id=dados.get("ws_client_id"),
            qr_payload=dados.get("qr_payload"),
            qr_code_base64=dados.get("qr_code_base64"),
            alerta_enviado=bool(dados.get("alerta_enviado", False)),
        )
        if dados.get("hora_chamada"):
            senha.hora_chamada = datetime.fromisoformat(dados["hora_chamada"])
        if dados.get("hora_atendida"):
            senha.hora_atendida = datetime.fromisoformat(dados["hora_atendida"])
        if dados.get("hora_cancelada"):
            senha.hora_cancelada = datetime.fromisoformat(dados["hora_cancelada"])
        return senha
