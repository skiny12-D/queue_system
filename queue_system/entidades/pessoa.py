from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class Pessoa:
    id: int
    nome: str
    contacto: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    prioridade: int = 0
    acesso_digital: bool = True

    def __str__(self) -> str:
        return f"Pessoa(id={self.id}, nome={self.nome})"

# comnetraio: marcador em entidade Pessoa
