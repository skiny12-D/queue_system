from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class Pessoa:
    id: int
    nome: str
    contacto: Optional[str] = None
    prioridade: int = 0

    def __str__(self) -> str:
        return f"Pessoa(id={self.id}, nome={self.nome})"
