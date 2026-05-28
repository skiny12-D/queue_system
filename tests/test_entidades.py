from datetime import datetime, timedelta

from queue_system.entidades.atendimento import Atendimento
from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.operadores import Operador


def test_pessoa_str():
    pessoa = Pessoa(id=1, nome="Ana", contacto="ana@example.com", email="ana@example.com", telefone="+351912345678")
    assert str(pessoa) == "Pessoa(id=1, nome=Ana)"
    assert pessoa.email == "ana@example.com"
    assert pessoa.telefone == "+351912345678"


def test_senha_estado_transitions():
    pessoa = Pessoa(id=1, nome="Carlos")
    senha = Senha(id=10, hora_emissao=datetime.now(), estado="emitida", pessoa=pessoa)
    senha.marcar_chamada()
    assert senha.estado == "chamada"
    senha.marcar_atendida()
    assert senha.estado == "atendida"


def test_senha_serialization_includes_qr():
    pessoa = Pessoa(id=2, nome="Beatriz", email="beatriz@example.com")
    senha = Senha(
        id=20,
        hora_emissao=datetime.now(),
        estado="emitida",
        pessoa=pessoa,
        via_emissao="digital",
        qr_payload="payload",
        qr_code_base64="YmFzZTY0",
    )
    dados = senha.to_dict()
    assert dados["via_emissao"] == "digital"
    assert dados["qr_payload"] == "payload"
    assert dados["qr_code_base64"] == "YmFzZTY0"


def test_atendimento_duracao_e_operador():
    pessoa = Pessoa(id=2, nome="Beatriz")
    senha = Senha(id=1, hora_emissao=datetime.now(), estado="emitida", pessoa=pessoa)
    operador = Operador(id=1, nome="Rui")
    atendimento = operador.iniciar_atendimento(senha, atendimento_id=1)
    assert atendimento.inicio is not None
    atendimento.fim = atendimento.inicio + timedelta(seconds=90)
    assert atendimento.duracao() == 90
