from __future__ import annotations

# comnetraio: marcador para localizar a API principal

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import qrcode
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from queue_system.entidades.pessoa import Pessoa
from queue_system.entidades.senha import Senha
from queue_system.gestor import GestorFila
from queue_system.monitor import MonitorAgencia
from queue_system.painel import PainelConsulta
from queue_system.operadores import Operador
from queue_system.notificador import notificar_usuario

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()

    async def _proximity_watcher() -> None:
        threshold = int(os.environ.get("ALERT_THRESHOLD", "4"))
        interval = float(os.environ.get("ALERT_CHECK_INTERVAL", "5"))
        while not stop_event.is_set():
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
                logger.exception("Erro no watcher de proximidade")
            await asyncio.sleep(interval)

    task = asyncio.create_task(_proximity_watcher())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Queue System",
    description="API de gestão de filas com monitorização online e interface web interativa.",
    version="0.1.0",
    lifespan=lifespan,
)

STATE_FILE = Path(__file__).resolve().parent.parent / "queue_state.json"
gestor = GestorFila(capacidade=100, politica="FIFO", persistencia=STATE_FILE)
monitor = MonitorAgencia("agencia-principal", gestor)
painel = PainelConsulta(gestor)
operador_principal = Operador(id=1, nome="Operador Principal")
_atendimento_counter = 1

STATIC_DIR = Path(__file__).resolve().parent / "static"
if (STATIC_DIR / "Site").exists():
    app.mount("/Site", StaticFiles(directory=str(STATIC_DIR / "Site")), name="site")
if (STATIC_DIR / "Painel").exists():
    app.mount("/Painel", StaticFiles(directory=str(STATIC_DIR / "Painel")), name="painel")

PUBLIC_WS_CLIENTS: Dict[str, WebSocket] = {}
PANEL_WS_CONNECTIONS: list[WebSocket] = []
current_epoch = "normal"
USERS = {
    "admin": {"senha": "123", "nome": "Administrador", "papel": "admin", "dept": None},
    "tesouraria": {"senha": "tes", "nome": "Gestor Tesouraria", "papel": "gestor", "dept": "Tesouraria"},
    "secretaria": {"senha": "sec", "nome": "Gestor Secretaria", "papel": "gestor", "dept": "Secretaria"},
}

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
    pessoa: Dict[str, Any]


def _senha_para_dict(senha: Senha) -> dict:
    return {
        "id": senha.id,
        "ticket_id": senha.ticket_id,
        "departamento": senha.departamento,
        "prioridade_label": senha.prioridade_label,
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

class SIGFJoinRequest(BaseModel):
    departamento: str
    prioridade: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    ws_client_id: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

async def _broadcast_public(message: dict) -> None:
    stale_clients: list[str] = []
    for client_id, websocket in PUBLIC_WS_CLIENTS.items():
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            stale_clients.append(client_id)
    for client_id in stale_clients:
        PUBLIC_WS_CLIENTS.pop(client_id, None)

async def notify_public_status() -> None:
    dados = {
        "tipo": "estado_fila",
        "dados": {
            "epoch": current_epoch,
            "filas": {
                dept: {
                    "quantidade": len(gestor.listar_fila(departamento=dept)),
                    "tempo_estimado_min": len(gestor.listar_fila(departamento=dept)) * 5,
                    "senhas": [senha.to_dict() for senha in gestor.listar_fila(departamento=dept)[:10]],
                }
                for dept in ["Tesouraria", "Secretaria"]
            },
        },
    }
    await _broadcast_public(dados)

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
                <button onclick="carregarQr()">Ver QR code</button>
                <pre id="posicaoResposta"></pre>
                <div id="qrContainer" style="margin-top: 1rem; display:none;">
                    <h3>QR code</h3>
                    <img id="qrImage" alt="QR code" style="max-width:100%; border:1px solid #ccc; padding: 0.5rem; background:#fff;" />
                    <p id="qrMensagem" style="color:#666; font-size:0.9rem;"></p>
                </div>
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
                    const result = await res.json();
                document.getElementById('emitirResposta').textContent = JSON.stringify(result, null, 2);
                if (result.qr_code_base64) {
                    document.getElementById('qrContainer').style.display = 'block';
                    document.getElementById('qrImage').src = `data:image/png;base64,${result.qr_code_base64}`;
                    document.getElementById('qrMensagem').textContent = 'Digitalize este QR code com o telefone ou tablet para aceder à sua senha.';
                } else {
                    document.getElementById('qrContainer').style.display = 'none';
                }
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
                async function carregarQr() {
                    const id = document.getElementById('posicaoId').value;
                    const res = await fetch(`/fila/qr/${id}`);
                    if (!res.ok) {
                        document.getElementById('qrMensagem').textContent = 'QR code não disponível para esta senha.';
                        document.getElementById('qrContainer').style.display = 'block';
                        document.getElementById('qrImage').src = '';
                        return;
                    }
                    const data = await res.json();
                    document.getElementById('qrContainer').style.display = 'block';
                    document.getElementById('qrImage').src = `data:image/png;base64,${data.qr_code_base64}`;
                    document.getElementById('qrMensagem').textContent = 'Digitalize este QR code com o telefone ou tablet para aceder à sua senha.';
                }
            </script>
        </body>
    </html>
    """

@app.get("/sigf")
def sigf_root() -> RedirectResponse:
    return RedirectResponse(url="/Site/Front/esqueleto.html")

@app.get("/api/queue/status")
def queue_status() -> dict:
    total = len(gestor.listar_fila())
    return {"total_na_fila": total, "epoch": current_epoch}

@app.get("/api/queue/tipos-servico")
def queue_tipos_servico() -> dict:
    tipos = {"verde": {"label": "Serviço Geral"}}
    if current_epoch == "exames":
        tipos["amarela"] = {"label": "Recurso / Exame"}
    elif current_epoch == "inscricoes":
        tipos["azul"] = {"label": "Inscrição / Matrícula"}
    return {"tipos": tipos}

@app.post("/api/queue/join")
async def queue_join(req: SIGFJoinRequest) -> dict:
    departamento = req.departamento if req.departamento in {"Tesouraria", "Secretaria"} else "Geral"
    prioridade_label = req.prioridade if req.prioridade in {"verde", "amarela", "azul"} else "verde"
    prioridade_value = {"verde": 0, "amarela": 1, "azul": 2}.get(prioridade_label, 0)
    cliente = Pessoa(
        id=0,
        nome="Cliente SIGF",
        contacto=None,
        email=req.email,
        telefone=req.telefone,
        prioridade=prioridade_value,
        acesso_digital=bool(req.email or req.telefone),
    )
    senha = gestor.emitir_senha(
        cliente,
        departamento=departamento,
        prioridade_label=prioridade_label,
        ws_client_id=req.ws_client_id,
    )
    if req.email or req.telefone:
        contact_info = {"email": req.email, "telefone": req.telefone}
        gestor.register_notification_contact(senha.id, contact_info)
        mensagem = f"A sua senha {senha.ticket_id} foi emitida."
        try:
            notificar_usuario(req.email, req.telefone, mensagem)
        except Exception:
            pass
    await notify_public_status()
    return {
        "ticket_id": senha.ticket_id,
        "departamento": senha.departamento,
        "posicao": gestor.posicao(senha.id, departamento=departamento),
        "tempo_estimado_min": len(gestor.listar_fila(departamento=departamento)) * 5,
        "prioridade": prioridade_label,
    }

@app.get("/api/ticket/{ticket_id}/pdf")
async def get_ticket_pdf(ticket_id: str) -> Response:
    senha = gestor.obter_senha_por_ticket_id(ticket_id)
    if senha is None:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="Dependência 'fpdf' não instalada")
    import io

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(f"SIGF-VALID:{ticket_id}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img_qr.save(buffer, format="PNG")
    buffer.seek(0)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, "SIGF - Senha de Atendimento", ln=True, align="C")
    pdf.set_font("Arial", 'B', 48)
    pdf.cell(0, 35, ticket_id, ln=True, align="C")
    pdf.image(buffer, x=75, y=70, w=60)
    pdf.set_font("Arial", '', 12)
    pdf.set_y(140)
    pdf.cell(0, 10, f"Departamento: {senha.departamento}", ln=True, align="C")
    pdf.cell(0, 10, f"Gerado em: {senha.hora_emissao.strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf_content = pdf.output(dest='S').encode('latin-1')
    return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=senha_{ticket_id}.pdf"})

@app.post("/api/chamar")
async def api_chamar(data: dict) -> dict:
    departamento = data.get("dept")
    senha = gestor.chamar_proximo(departamento=departamento) if departamento else gestor.chamar_proximo()
    if senha is None:
        raise HTTPException(status_code=404, detail="Fila vazia")
    if senha.ws_client_id in PUBLIC_WS_CLIENTS:
        try:
            await PUBLIC_WS_CLIENTS[senha.ws_client_id].send_text(json.dumps({
                "tipo": "senha_chamada",
                "mensagem": f"Senha {senha.ticket_id} chamada para o atendimento.",
                "ticket_id": senha.ticket_id,
            }))
        except Exception:
            PUBLIC_WS_CLIENTS.pop(senha.ws_client_id, None)
    await notify_public_status()
    return {"chamada": _senha_para_dict(senha)}

@app.post("/api/login")
def api_login(payload: LoginRequest) -> dict:
    user = USERS.get(payload.username)
    if user and user["senha"] == payload.password:
        return {
            "nome": user["nome"],
            "papel": user["papel"],
            "dept": user["dept"],
        }
    raise HTTPException(status_code=401, detail="Credenciais inválidas")

@app.post("/api/admin/set-epoch")
def api_set_epoch(payload: dict) -> dict:
    epoch = str(payload.get("epoch", "normal"))
    if epoch not in {"normal", "exames", "inscricoes"}:
        raise HTTPException(status_code=400, detail="Época inválida")
    global current_epoch
    current_epoch = epoch
    return {"epoch": current_epoch}

@app.post("/api/gestor/toggle")
def api_gestor_toggle(payload: dict) -> dict:
    gestor_id = payload.get("gestor_id")
    if gestor_id is None:
        raise HTTPException(status_code=400, detail="gestor_id é obrigatório")
    return {"status": "ok", "gestor_id": gestor_id}

@app.get("/api/estado")
def api_estado() -> dict:
    return {
        "epoch": current_epoch,
        "filas": {
            dept: {
                "total": len(gestor.listar_fila(departamento=dept)),
                "tempo_medio": len(gestor.listar_fila(departamento=dept)) * 5,
                "senhas": [senha.to_dict() for senha in gestor.listar_fila(departamento=dept)[:10]],
            }
            for dept in ["Tesouraria", "Secretaria"]
        },
        "total_chamadas_hoje": 0,
    }

@app.post("/api/avaliacao")
def api_avaliacao(payload: dict) -> dict:
    estrelas = payload.get("estrelas")
    comentario = payload.get("comentario", "")
    if not isinstance(estrelas, int) or estrelas < 1 or estrelas > 5:
        raise HTTPException(status_code=400, detail="Estrelas inválidas")
    logger.info("Avaliação recebida: %s estrelas, comentário: %s", estrelas, comentario)
    return {"status": "avaliacao registrada"}

@app.websocket("/ws/public/{client_id}")
async def websocket_publico(websocket: WebSocket, client_id: str) -> None:
    await websocket.accept()
    PUBLIC_WS_CLIENTS[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        PUBLIC_WS_CLIENTS.pop(client_id, None)

@app.websocket("/ws/painel")
async def websocket_painel(websocket: WebSocket) -> None:
    await websocket.accept()
    PANEL_WS_CONNECTIONS.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        PANEL_WS_CONNECTIONS.remove(websocket)

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
