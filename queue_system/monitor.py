from __future__ import annotations

from statistics import mean
from typing import List

from queue_system.gestor import GestorFila
from queue_system.entidades.atendimento import Atendimento

class MonitorAgencia:
    def __init__(self, agencia: str, gestor: GestorFila):
        self.agencia = agencia
        self.gestor = gestor
        self.atendimentos: List[Atendimento] = []

    def consultar_fila(self) -> int:
        return len(self.gestor.listar_fila())

    def listar_agencias(self) -> List[str]:
        return [self.agencia]

    def avaliar_velocidade(self) -> str:
        duracoes = [atendimento.duracao() for atendimento in self.atendimentos if atendimento.duracao() is not None]
        if not duracoes:
            return "média"
        media_segundos = mean(duracoes)
        if media_segundos <= 120:
            return "rápida"
        if media_segundos <= 300:
            return "média"
        return "lenta"

    def estado_agencia(self) -> dict:
        return {
            "agencia": self.agencia,
            "fila": self.consultar_fila(),
            "velocidade": self.avaliar_velocidade(),
            "politica": self.gestor.politica,
            "capacidade": self.gestor.capacidade,
        }

    def registrar_atendimento(self, atendimento: Atendimento) -> None:
        if atendimento.fim is not None:
            self.atendimentos.append(atendimento)
