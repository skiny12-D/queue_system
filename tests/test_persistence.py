from pathlib import Path

from queue_system.gestor import GestorFila
from queue_system.entidades.pessoa import Pessoa


def test_gestor_persistence(tmp_path):
    state_file = tmp_path / "queue_state.json"

    gestor = GestorFila(capacidade=5, politica="FIFO", persistencia=state_file)
    pessoa = Pessoa(id=42, nome="Test User", contacto="cont", email="t@example.com", telefone="+351", prioridade=1, acesso_digital=True)
    s = gestor.emitir_senha(pessoa, departamento="Tesouraria")

    # Cria novo gestor apontando para o mesmo ficheiro de persistência
    gestor2 = GestorFila(capacidade=10, politica="FIFO", persistencia=state_file)

    # O estado persistido deve conter a senha emitida
    filas = gestor2.listar_fila()
    assert any(item.id == s.id for item in filas)
