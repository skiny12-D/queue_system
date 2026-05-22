import threading

import pytest

from queue_system.entidades.pessoa import Pessoa
from queue_system.gestor import GestorFila


def test_emitir_e_posicao_e_chamar():
    gestor = GestorFila(capacidade=5, politica="FIFO")
    pessoa1 = Pessoa(id=1, nome="Ana")
    pessoa2 = Pessoa(id=2, nome="Bruno")
    senha1 = gestor.emitir_senha(pessoa1)
    senha2 = gestor.emitir_senha(pessoa2)
    assert gestor.posicao(senha1.id) == 1
    assert gestor.posicao(senha2.id) == 2
    chamada = gestor.chamar_proximo()
    assert chamada is not None
    assert chamada.id == senha1.id
    assert chamada.estado == "chamada"


def test_cancelar_senha():
    gestor = GestorFila(capacidade=2, politica="FIFO")
    pessoa = Pessoa(id=1, nome="Ana")
    senha = gestor.emitir_senha(pessoa)
    pos = gestor.cancelar_senha(senha.id)
    assert pos == 1
    with pytest.raises(ValueError):
        gestor.posicao(senha.id)


def test_politica_lifo():
    gestor = GestorFila(capacidade=3, politica="LIFO")
    a = gestor.emitir_senha(Pessoa(id=1, nome="Ana"))
    b = gestor.emitir_senha(Pessoa(id=2, nome="Bruno"))
    chamada = gestor.chamar_proximo()
    assert chamada.id == b.id


def test_politica_prioridade():
    gestor = GestorFila(capacidade=3, politica="PRIORIDADE")
    gestor.emitir_senha(Pessoa(id=1, nome="Ana", prioridade=0))
    gestor.emitir_senha(Pessoa(id=2, nome="Bruno", prioridade=5))
    chamada = gestor.chamar_proximo()
    assert chamada is not None
    assert chamada.pessoa.prioridade == 5


def test_concorrencia_emissao():
    gestor = GestorFila(capacidade=100, politica="FIFO")
    erros = []

    def emitir(i: int):
        try:
            gestor.emitir_senha(Pessoa(id=i, nome=f"Cliente {i}"))
        except Exception as exc:
            erros.append(exc)

    threads = [threading.Thread(target=emitir, args=(i,)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(gestor.listar_fila()) == 20
    assert not erros


def test_capacidade_atingida():
    gestor = GestorFila(capacidade=1, politica="FIFO")
    gestor.emitir_senha(Pessoa(id=1, nome="Ana"))
    with pytest.raises(ValueError):
        gestor.emitir_senha(Pessoa(id=2, nome="Bruno"))
