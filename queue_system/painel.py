from __future__ import annotations

from typing import Optional

from queue_system.gestor import GestorFila
from queue_system.entidades.senha import Senha

class PainelConsulta:
    def __init__(self, gestor: GestorFila):
        self.gestor = gestor

    def consultar_posicao(self, senha_id: int) -> int:
        return self.gestor.posicao(senha_id)

    def proxima_senha(self) -> Optional[Senha]:
        fila = self.gestor.listar_fila()
        return fila[0] if fila else None
