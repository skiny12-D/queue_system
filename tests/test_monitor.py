from datetime import datetime, timedelta

from queue_system.entidades.atendimento import Atendimento
from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.gestor import GestorFila
from queue_system.monitor import MonitorAgencia
from queue_system.operadores import Operador


def test_monitor_agencia_estado():
    gestor = GestorFila(capacidade=10, politica="FIFO")
    monitor = MonitorAgencia("central", gestor)
    assert monitor.listar_agencias() == ["central"]
    assert monitor.consultar_fila() == 0

    senha = gestor.emitir_senha(Pessoa(id=1, nome="Ana"))
    assert monitor.consultar_fila() == 1

    operador = Operador(id=1, nome="Rui")
    chamada = gestor.chamar_proximo()
    assert chamada is not None
    atendimento = operador.iniciar_atendimento(chamada, atendimento_id=1)
    atendimento.inicio = datetime.now() - timedelta(seconds=180)
    atendimento.terminar()
    monitor.registrar_atendimento(atendimento)
    assert monitor.avaliar_velocidade() == "média"
