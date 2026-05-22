from __future__ import annotations

from typing import Optional

from queue_system.entidades.atendimento import Atendimento
from queue_system.entidades.senha import Senha
from queue_system.gestor import GestorFila

class Operador:
    def __init__(self, id: int, nome: str):
        self.id = id
        self.nome = nome

    def chamar(self, gestor: GestorFila) -> Optional[Senha]:
        return gestor.chamar_proximo()

    def iniciar_atendimento(self, senha: Senha, atendimento_id: int) -> Atendimento:
        atendimento = Atendimento(id=atendimento_id, senha=senha, operador=self)
        atendimento.iniciar()
        return atendimento

    def terminar_atendimento(self, atendimento: Atendimento) -> Atendimento:
        atendimento.terminar()
        return atendimento

    def __str__(self) -> str:
        return f"Operador(id={self.id}, nome={self.nome})"
