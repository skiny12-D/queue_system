from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.gestor import GestorFila
from queue_system.monitor import MonitorAgencia
from queue_system.painel import PainelConsulta
from queue_system.operadores import Operador
from queue_system.notificador import notificar_usuario
import os
import threading
import time

app = FastAPI(
    title="Queue System",
    description="API de gestão de filas com monitorização online e interface web interativa.",
    version="0.1.0",
)

STATE_FILE = Path(__file__).resolve().parent.parent / "queue_state.json"
gestor = GestorFila(capacidade=100, politica="FIFO", persistencia=STATE_FILE)
monitor = MonitorAgencia("agencia-principal", gestor)
painel = PainelConsulta(gestor)
operador_principal = Operador(id=1, nome="Operador Principal")
_atendimento_counter = 1

class PessoaInput(BaseModel):
    id: int
    nome: str
    contacto: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    prioridade: int = 0
    acesso_digital: bool = True

class SenhaOutput(BaseModel):
    id: int
    estado: str
    hora_emissao: str
    via_emissao: str
    qr_code_base64: Optional[str] = None
    pessoa: Dict[str, Optional[str]]


def _senha_para_dict(senha: Senha) -> dict:
    return {
        "id": senha.id,
        "estado": senha.estado,
        "hora_emissao": senha.hora_emissao.isoformat(),
        "via_emissao": senha.via_emissao,
        "qr_code_base64": senha.qr_code_base64,
        "pessoa": {
            "id": senha.pessoa.id,
            "nome": senha.pessoa.nome,
            "contacto": senha.pessoa.contacto,
            "email": senha.pessoa.email,
            "telefone": senha.pessoa.telefone,
            "prioridade": senha.pessoa.prioridade,
            "acesso_digital": senha.pessoa.acesso_digital,
        },
    }

@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <html>
        <head>
            <title>Queue System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 2rem; }
                section { margin-bottom: 2rem; }
                input, button { padding: 0.5rem; margin: 0.25rem 0; }
                .box { border: 1px solid #ddd; padding: 1rem; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>Queue System</h1>
            <section class="box">
                <h2>Emitir nova senha</h2>
                <label>Id: <input id="pessoaId" type="number" value="1"></label><br>
                <label>Nome: <input id="pessoaNome" type="text" value="Ana"></label><br>
                <label>Contacto: <input id="pessoaContacto" type="text" value="ana@example.com"></label><br>
                <label>E-mail: <input id="pessoaEmail" type="email" value="ana@example.com"></label><br>
                <label>Telefone: <input id="pessoaTelefone" type="tel" value=""></label><br>
                <label>Acesso digital: <input id="pessoaAcessoDigital" type="checkbox" checked></label><br>
                <label>Prioridade: <input id="pessoaPrioridade" type="number" value="0"></label><br>
                <button onclick="emitirSenha()">Emitir senha</button>
                <pre id="emitirResposta"></pre>
            </section>
            <section class="box">
                <h2>Chamar próximo</h2>
                <button onclick="chamarProximo()">Chamar</button>
                <pre id="chamarResposta"></pre>
            </section>
            <section class="box">
                <h2>Consultar posição</h2>
                <label>Senha id: <input id="posicaoId" type="number" value="1"></label><br>
                <button onclick="consultarPosicao()">Consultar</button>
                <button onclick="verAlerta()">Ver alerta de proximidade</button>
                <pre id="posicaoResposta"></pre>
            </section>
            <section class="box">
                <h2>Cancelar senha</h2>
                <label>Senha id: <input id="cancelarId" type="number" value="1"></label><br>
                <button onclick="cancelarSenha()">Cancelar</button>
                <pre id="cancelarResposta"></pre>
            </section>
            <section class="box">
                <h2>Fila atual</h2>
                <button onclick="listarFila()">Listar fila</button>
                <pre id="listaResposta"></pre>
            </section>
            <section class="box">
                <h2>Monitorização</h2>
                <button onclick="verMonitor()">Ver estado da agência</button>
                <pre id="monitorResposta"></pre>
            </section>
            <script>
                async function emitirSenha() {
                    const body = {
                        id: Number(document.getElementById('pessoaId').value),
                        nome: document.getElementById('pessoaNome').value,
                        contacto: document.getElementById('pessoaContacto').value,
                        email: document.getElementById('pessoaEmail').value,
                        telefone: document.getElementById('pessoaTelefone').value,
                        prioridade: Number(document.getElementById('pessoaPrioridade').value),
                        acesso_digital: document.getElementById('pessoaAcessoDigital').checked,
                    };
                    const res = await fetch('/fila/emitir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                    document.getElementById('emitirResposta').textContent = JSON.stringify(await res.json(), null, 2);
                }
                async function chamarProximo() {
                    const res = await fetch('/fila/chamar', { method: 'POST' });
                    document.getElementById('chamarResposta').textContent = await res.text();
                }
                async function consultarPosicao() {
                    const id = document.getElementById('posicaoId').value;
                    const res = await fetch(`/fila/posicao/${id}`);
                    document.getElementById('posicaoResposta').textContent = await res.text();
                }
                async function cancelarSenha() {
                    const id = document.getElementById('cancelarId').value;
                    const res = await fetch(`/fila/cancelar/${id}`, { method: 'POST' });
                    document.getElementById('cancelarResposta').textContent = await res.text();
                }
                async function listarFila() {
                    const res = await fetch('/fila/listar');
                    document.getElementById('listaResposta').textContent = JSON.stringify(await res.json(), null, 2);
                }
                async function verMonitor() {
                    const res = await fetch('/monitor/agencias/agencia-principal');
                    document.getElementById('monitorResposta').textContent = JSON.stringify(await res.json(), null, 2);
                }
                async function verAlerta() {
                    const id = document.getElementById('posicaoId').value;
                    const res = await fetch(`/fila/alerta/${id}`);
                    document.getElementById('posicaoResposta').textContent = JSON.stringify(await res.json(), null, 2);
                }
            </script>
        </body>
    </html>
    """

@app.post("/fila/emitir", response_model=SenhaOutput)
def emitir_senha(pessoa: PessoaInput) -> dict:
    # Não persistir contactos do utilizador: registamos contacto apenas para notificação temporária
    persisted_cliente = Pessoa(
        id=pessoa.id,
        nome=pessoa.nome,
        contacto=None,
        email=None,
        telefone=None,
        prioridade=pessoa.prioridade,
        acesso_digital=pessoa.acesso_digital,
    )
    senha = gestor.emitir_senha(persisted_cliente)
    # Registar contacto temporário para notificações (não persistido)
    contact_info = {"email": pessoa.email, "telefone": pessoa.telefone}
    if pessoa.email or pessoa.telefone:
        gestor.register_notification_contact(senha.id, contact_info)
        # enviar notificação inicial (tentativa); não falhar a API se não for possível
        mensagem = f"A sua senha {senha.id} foi emitida."
        try:
            notificar_usuario(pessoa.email, pessoa.telefone, mensagem)
        except Exception:
            pass
    return _senha_para_dict(senha)


@app.on_event("startup")
def start_proximity_watcher() -> None:
    def _proximity_watcher() -> None:
        threshold = int(os.environ.get("ALERT_THRESHOLD", "4"))
        interval = float(os.environ.get("ALERT_CHECK_INTERVAL", "5"))
        while True:
            try:
                fila = gestor.listar_fila()
                for senha in list(fila):
                    if senha.via_emissao == "digital" and not senha.alerta_enviado:
                        try:
                            pos = gestor.posicao(senha.id)
                        except ValueError:
                            continue
                        if pos <= threshold:
                            contact = gestor.get_notification_contact(senha.id)
                            mensagem = f"A sua senha {senha.id} está próxima (posição {pos})."
                            if contact:
                                try:
                                    notificar_usuario(contact.get("email"), contact.get("telefone"), mensagem)
                                except Exception:
                                    pass
                            senha.alerta_enviado = True
                            gestor._salvar_estado()
            except Exception:
                pass
            time.sleep(interval)

    thread = threading.Thread(target=_proximity_watcher, daemon=True)
    thread.start()

@app.get("/fila/qr/{senha_id}")
def qr_senha(senha_id: int) -> dict:
    senha = gestor.obter_senha(senha_id)
    if senha is None or senha.qr_code_base64 is None:
        raise HTTPException(status_code=404, detail="QR code não disponível para esta senha")
    return {"qr_code_base64": senha.qr_code_base64}

@app.get("/fila/alerta/{senha_id}")
def alerta_proxima_senha(senha_id: int) -> dict:
    try:
        pos = gestor.posicao(senha_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    senha = gestor.obter_senha(senha_id)
    alerta = False
    if senha is not None and senha.via_emissao == "digital" and pos <= 4:
        alerta = True
    return {"alerta": alerta, "posicao": pos, "via_emissao": senha.via_emissao if senha else None}

@app.post("/fila/chamar", response_model=Optional[SenhaOutput])
def chamar_senha() -> Optional[dict]:
    senha = operador_principal.chamar(gestor)
    if senha is None:
        raise HTTPException(status_code=404, detail="Fila vazia")
    return _senha_para_dict(senha)

@app.get("/fila/posicao/{senha_id}")
def posicao_senha(senha_id: int) -> dict:
    try:
        pos = gestor.posicao(senha_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"posicao": pos}

@app.post("/fila/cancelar/{senha_id}")
def cancelar_senha(senha_id: int) -> dict:
    try:
        pos = gestor.cancelar_senha(senha_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"cancelado": senha_id, "posicao_anterior": pos}

@app.get("/fila/listar")
def listar_fila() -> list[dict]:
    return [_senha_para_dict(senha) for senha in gestor.listar_fila()]

@app.get("/monitor/agencias")
def listar_agencias() -> dict:
    return {"agencias": monitor.listar_agencias()}

@app.get("/monitor/agencias/{agencia}")
def estado_agencia(agencia: str) -> dict:
    if agencia != monitor.agencia:
        raise HTTPException(status_code=404, detail="Agência não encontrada")
    return monitor.estado_agencia()

@app.get("/monitor/velocidade")
def velocidade() -> dict:
    return {"velocidade": monitor.avaliar_velocidade()}

@app.post("/operador/chamar")
def operador_chamar() -> dict:
    senha = operador_principal.chamar(gestor)
    if senha is None:
        raise HTTPException(status_code=404, detail="Fila vazia")
    return _senha_para_dict(senha)
