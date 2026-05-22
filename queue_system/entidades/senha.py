from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from queue_system.entidades.pessoa import Pessoa

@dataclass
class Senha:
    id: int
    hora_emissao: datetime
    estado: str
    pessoa: Pessoa
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
            "pessoa": {
                "id": self.pessoa.id,
                "nome": self.pessoa.nome,
                "contacto": self.pessoa.contacto,
                "prioridade": self.pessoa.prioridade,
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
            prioridade=int(dados["pessoa"].get("prioridade", 0)),
        )
        senha = Senha(
            id=int(dados["id"]),
            hora_emissao=datetime.fromisoformat(dados["hora_emissao"]),
            estado=str(dados["estado"]),
            pessoa=pessoa,
        )
        if dados.get("hora_chamada"):
            senha.hora_chamada = datetime.fromisoformat(dados["hora_chamada"])
        if dados.get("hora_atendida"):
            senha.hora_atendida = datetime.fromisoformat(dados["hora_atendida"])
        if dados.get("hora_cancelada"):
            senha.hora_cancelada = datetime.fromisoformat(dados["hora_cancelada"])
        return senha
