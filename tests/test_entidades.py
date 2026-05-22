from datetime import datetime, timedelta

from queue_system.entidades.atendimento import Atendimento
from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.operadores import Operador


def test_pessoa_str():
    pessoa = Pessoa(id=1, nome="Ana", contacto="ana@example.com")
    assert str(pessoa) == "Pessoa(id=1, nome=Ana)"


def test_senha_estado_transitions():
    pessoa = Pessoa(id=1, nome="Carlos")
    senha = Senha(id=10, hora_emissao=datetime.now(), estado="emitida", pessoa=pessoa)
    senha.marcar_chamada()
    assert senha.estado == "chamada"
    senha.marcar_atendida()
    assert senha.estado == "atendida"


def test_atendimento_duracao_e_operador():
    pessoa = Pessoa(id=2, nome="Beatriz")
    senha = Senha(id=1, hora_emissao=datetime.now(), estado="emitida", pessoa=pessoa)
    operador = Operador(id=1, nome="Rui")
    atendimento = operador.iniciar_atendimento(senha, atendimento_id=1)
    assert atendimento.inicio is not None
    atendimento.fim = atendimento.inicio + timedelta(seconds=90)
    assert atendimento.duracao() == 90
