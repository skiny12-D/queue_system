from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from queue_system.entidades.senha import Senha

if TYPE_CHECKING:
    from queue_system.operadores import Operador

# comnetraio: marcador em entidade Atendimento

@dataclass
class Atendimento:
    id: int
    senha: Senha
    operador: Operador
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None

    def iniciar(self) -> None:
        if self.inicio is not None:
            return
        self.inicio = datetime.now()

    def terminar(self) -> None:
        if self.fim is not None:
            return
        self.fim = datetime.now()
        self.senha.marcar_atendida()

    def duracao(self) -> Optional[float]:
        if self.inicio is None or self.fim is None:
            return None
        return (self.fim - self.inicio).total_seconds()
