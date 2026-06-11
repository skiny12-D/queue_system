from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from queue_system.api import app
from queue_system.entidades.pessoa import Pessoa
from queue_system.gestor import GestorFila
from queue_system.monitor import MonitorAgencia
from queue_system.painel import PainelConsulta


@pytest.fixture(autouse=True)
def client(monkeypatch, tmp_path):
    state_file = tmp_path / "queue_state.json"
    gestor = GestorFila(capacidade=10, politica="FIFO", persistencia=state_file)
    monitor = MonitorAgencia("test", gestor)
    painel = PainelConsulta(gestor)
    monkeypatch.setattr("queue_system.api.gestor", gestor)
    monkeypatch.setattr("queue_system.api.monitor", monitor)
    monkeypatch.setattr("queue_system.api.painel", painel)
    monkeypatch.setattr("queue_system.api.current_epoch", "normal")
    yield TestClient(app)


def test_api_queue_status_empty(client):
    response = client.get("/api/queue/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_na_fila"] == 0
    assert data["epoch"] == "normal"


def test_api_set_epoch(client):
    response = client.post("/api/admin/set-epoch", json={"epoch": "exames"})
    assert response.status_code == 200
    assert response.json() == {"epoch": "exames"}


def test_api_gestor_toggle(client):
    response = client.post("/api/gestor/toggle", json={"gestor_id": "admin"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "gestor_id": "admin"}


def test_api_estado_has_required_fields(client):
    response = client.get("/api/estado")
    assert response.status_code == 200
    data = response.json()
    assert data["epoch"] == "normal"
    assert "filas" in data
    assert set(data["filas"].keys()) == {"Tesouraria", "Secretaria"}


def test_api_avaliacao_accepts_valid_payload(client):
    response = client.post("/api/avaliacao", json={"estrelas": 4, "comentario": "Bom serviço"})
    assert response.status_code == 200
    assert response.json() == {"status": "avaliacao registrada"}


def test_api_avaliacao_rejects_invalid_stars(client):
    response = client.post("/api/avaliacao", json={"estrelas": 6})
    assert response.status_code == 400
    assert response.json()["detail"] == "Estrelas inválidas"


def test_fila_emitir_and_posicao(client):
    response = client.post("/fila/emitir", json={
        "id": 1,
        "nome": "Ana",
        "contacto": "ana@example.com",
        "email": "ana@example.com",
        "telefone": "+351912345678",
        "prioridade": 1,
        "acesso_digital": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["estado"] == "emitida"
    pos_response = client.get(f"/fila/posicao/{data['id']}")
    assert pos_response.status_code == 200
    assert pos_response.json()["posicao"] == 1
