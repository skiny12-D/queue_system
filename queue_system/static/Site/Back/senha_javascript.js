/* ============================================================
   SIGF — Sistema Inteligente de Gestão de Filas
   ============================================================ */

'use strict';

// =====================================================================
// 1. CONFIGURAÇÃO GLOBAL
// ======================================================================

// Deteta automaticamente o host actual para evitar bloqueios de segurança
const API = window.location.origin;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/public`;

// IDs de cliente WebSocket únicos por sessão
const wsClientId = 'pub_' + Math.random().toString(36).slice(2, 10);

// Estado da aplicação
let ws              = null;
let selectedDept    = null;
let currentTicketId = null;
let currentTab      = 'Tesouraria';
let filaData        = {};
let toastTimer      = null;
let wsKeepalive     = null;
let httpFallback    = null;

// Mapeamento de épocas para badge
const EPOCH_MAP = {
  normal:     { label: '📋 Dias Normais',           cls: 'normal'     },
  exames:     { label: '📝 Época de Exames',         cls: 'exames'     },
  inscricoes: { label: '🎓 Inscrições e Matrículas', cls: 'inscricoes' },
};

// Mapeamento de prioridades para labels
const PRIO_LABELS = {
  verde:   'Serviço Geral',
  amarela: 'Recurso / Exame',
  azul:    'Inscrição / Matrícula',
};

// =================================================
// 2. WEBSOCKET — Ligação em tempo real
// =================================================

/**
 * Estabelece a ligação WebSocket com reconexão automática.
 * Em caso de falha, o fallback HTTP toma conta das actualizações.
 */
function conectarWS() {
  // Limpa keepalive anterior se existir
  if (wsKeepalive) clearInterval(wsKeepalive);

  try {
    ws = new WebSocket(`${WS_URL}/${wsClientId}`);
  } catch {
    setWsStatus(false);
    return;
  }

  ws.onopen = () => {
    setWsStatus(true);

    // Keepalive a cada 25s para evitar timeout do servidor
    wsKeepalive = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 25_000);
  };

  ws.onmessage = (e) => {
    // Ignora pongs e mensagens não-JSON
    if (e.data === 'pong') return;
    try {
      const msg = JSON.parse(e.data);
      handleWsMessage(msg);
    } catch {
      // Mensagem não-JSON ignorada
    }
  };

  ws.onclose = () => {
    setWsStatus(false);
    if (wsKeepalive) clearInterval(wsKeepalive);
    // Tenta reconectar após 3 segundos
    setTimeout(conectarWS, 3_000);
  };

  ws.onerror = () => {
    setWsStatus(false);
  };
}

/**
 * Processa as mensagens recebidas pelo WebSocket.
 * @param {Object} msg - Mensagem JSON parsed
 */
function handleWsMessage(msg) {
  switch (msg.tipo) {
    case 'estado_fila':
      atualizarPainel(msg.dados);
      break;

    case 'senha_chamada':
      notificarSistema('Sua senha foi chamada!', msg.mensagem);
      showToast(`📢 ${msg.mensagem}`, 'success', 8000);
      // Destaca visualmente a senha chamada na lista
      highlightSenhaChamada(msg.ticket_id || msg.id);
      break;

    case 'alerta_20min':
      mostrarAlerta20();
      showToast(`⏰ ${msg.mensagem}`, 'warning', 10000);
      break;

    case 'senha_removida':
      // Actualiza a fila após remoção de uma senha
      if (msg.dados) atualizarPainel(msg.dados);
      break;

    default:
      break;
  }
}

/**
 * Actualiza o indicador visual de ligação WS.
 * @param {boolean} online
 */
function setWsStatus(online) {
  const dot = document.getElementById('wsDot');
  const lbl = document.getElementById('wsLbl');
  if (!dot || !lbl) return;

  dot.classList.toggle('on', online);
  lbl.textContent = online ? 'Em tempo real' : 'Desligado — a reconectar…';
}

/**
 * Destaca brevemente a linha da senha chamada na lista do painel.
 * @param {string|null} ticketId
 */
function highlightSenhaChamada(ticketId) {
  if (!ticketId) return;
  const items = document.querySelectorAll('.ticket-row');
  items.forEach(item => {
    if (item.querySelector('.tr-id')?.textContent === ticketId) {
      item.style.background = 'rgba(255, 239, 1, 0.2)';
      item.style.borderLeftColor = 'var(--g)';
      setTimeout(() => { item.style.background = ''; item.style.borderLeftColor = ''; }, 6000);
    }
  });
}

// ===========================================================================
// 3. FALLBACK HTTP — Actualização periódica se WS não estiver disponível
// ═==========================================================================

/**
 * Inicia o polling HTTP como fallback quando o WS está offline.
 * Apenas activo se o WS não estiver ligado.
 */
function iniciarFallbackHTTP() {
  httpFallback = setInterval(async () => {
    if (ws && ws.readyState === WebSocket.OPEN) return; // WS activo, fallback desnecessário
    try {
      const r = await fetch(`${API}/api/queue/status`);
      if (!r.ok) return;
      atualizarPainel(await r.json());
    } catch {
      // Silencioso
    }
  }, 5_000);
}

// ========================================================
// 4. PAINEL EM TEMPO REAL
// ========================================================

/**
 * Recebe os dados do estado da fila e actualiza toda a interface.
 * @param {Object} dados - Payload do backend
 */
function atualizarPainel(dados) {
  filaData = dados.filas || {};

  // Actualiza contagens nos botões de departamento
  const tes = filaData['Tesouraria'] || {};
  const sec = filaData['Secretaria'] || {};
  setText('countTes', `${tes.quantidade ?? 0} na fila`);
  setText('countSec', `${sec.quantidade ?? 0} na fila`);

  // Actualiza a tab actualmente visível
  atualizarTab(currentTab);

  // Actualiza o badge da época académica
  const ep = EPOCH_MAP[dados.epoch] || EPOCH_MAP.normal;
  const badge = document.getElementById('epochBadge');
  if (badge) {
    badge.textContent = ep.label;
    badge.className   = `epoch-badge ${ep.cls}`;
  }

  // Actualiza os tipos de serviço disponíveis para a nova época ativa
  carregarTiposServico();
}

/**
 * Actualiza as estatísticas e a lista de senhas do painel
 * para o departamento activo.
 * @param {string} dept - 'Tesouraria' ou 'Secretaria'
 */
function atualizarTab(dept) {
  currentTab = dept;
  const info = filaData[dept] || { quantidade: 0, tempo_estimado_min: 0, senhas: [] };

  // Estatísticas numéricas (Ajustado para os IDs novos do painel direito)
  setText('qsQtd', info.quantidade);
  setText('qsTempo', info.tempo_estimado_min);

  // Classificação
  const classEl = document.getElementById('qsCls');
  const dotEl   = document.getElementById('qsClsCls');
  if (classEl) {
    const { label, cls } = classificarFila(info.quantidade);
    classEl.textContent = label;
    if (dotEl) dotEl.className = `qs-cls ${cls}`;
  }

  // Lista das próximas senhas
  renderizarListaSenhas(info.senhas ?? []);
}

/**
 * Devolve o label e classe de classificação consoante o tamanho da fila.
 * @param {number} qtd
 * @returns {{ label: string, cls: string }}
 */
function classificarFila(qtd) {
  if (qtd > 10) return { label: 'Lenta',  cls: 'slow' };
  if (qtd > 4)  return { label: 'Média',  cls: 'medium' };
  return              { label: 'Rápida', cls: 'fast' };
}

/**
 * Renderiza a lista das próximas senhas no painel.
 * Limita a 15 entradas para não sobrecarregar o DOM.
 * @param {Array} senhas
 */
function renderizarListaSenhas(senhas) {
  const lista = document.getElementById('panelList');
  if (!lista) return;

  if (!senhas || senhas.length === 0) {
    lista.innerHTML = `<div class="panel-empty"><div class="pe-icon">✅</div>Fila vazia</div>`;
    return;
  }

  const PMAP = { verde: 'verde', amarela: 'amarela', azul: 'azul' };
  lista.innerHTML = senhas.slice(0, 15).map((s, i) => `
    <div class="ticket-row prio-${PMAP[s.prioridade] || 'verde'}" data-ticket="${s.id}">
      <div>
        <div class="tr-id">${s.id}</div>
        <div class="tr-dept">${s.departamento}</div>
      </div>
      <div class="tr-pos">
        <strong>${i + 1}º</strong>~${i * 5} min
      </div>
    </div>
  `).join('');
}

/**
 * Muda a tab activa do painel e actualiza os estilos.
 * @param {string} dept
 */
function switchTab(dept) {
  currentTab = dept;
  const tabTes = document.getElementById('tabTes');
  const tabSec = document.getElementById('tabSec');
  if (tabTes) tabTes.classList.toggle('active', dept === 'Tesouraria');
  if (tabSec) tabSec.classList.toggle('active', dept === 'Secretaria');
  atualizarTab(dept);
}

// =================================================
// 5. SELECÇÃO DE DEPARTAMENTO
// =================================================

/**
 * Selecciona um departamento, activa o botão correspondente,
 * liberta o botão de entrada na fila e sincroniza com o painel.
 * @param {string} dept - 'Tesouraria' ou 'Secretaria'
 */
function selectDept(dept) {
  selectedDept = dept;

  const btnTes = document.getElementById('btnTes');
  const btnSec = document.getElementById('btnSec');
  if (btnTes) btnTes.classList.toggle('selected', dept === 'Tesouraria');
  if (btnSec) btnSec.classList.toggle('selected', dept === 'Secretaria');

  // Activa o botão de entrada
  const btnEntrar = document.getElementById('btnEntrar');
  if (btnEntrar) btnEntrar.disabled = false;

  // Sincroniza tab do painel com o departamento escolhido
  switchTab(dept);

  // Carrega os tipos de serviço disponíveis para esta selecção
  carregarTiposServico();
}

// ==============================================
// 6. TIPOS DE SERVIÇO
// ===============================================

/**
 * Vai buscar ao backend os tipos de serviço disponíveis
 * e preenche o select. Usa o padrão se a API estiver offline.
 */
async function carregarTiposServico() {
  const sel = document.getElementById('tipoSelect');
  if (!sel) return;

  try {
    const r = await fetch(`${API}/api/queue/tipos-servico`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();

    sel.innerHTML = '';
    for (const [val, info] of Object.entries(d.tipos ?? {})) {
      const opt       = document.createElement('option');
      opt.value       = val;
      opt.textContent = info.label;
      sel.appendChild(opt);
    }
  } catch {
    // Fallback: opção padrão já no HTML, não altera
    console.info('SIGF: tipos de serviço usando opção padrão.');
  }
}

// ===========================================================
// 7. NOTIFICAÇÕES — Toggle dos campos opcionais
// ===========================================================

/**
 * Mostra ou esconde os campos de notificação
 * conforme o estado da checkbox.
 */
function toggleNotif() {
  const checked     = document.getElementById('chkNotif')?.checked ?? false;
  const notifFields = document.getElementById('notifFields');
  if (!notifFields) return;
  notifFields.classList.toggle('open', checked);

  // Foca o primeiro campo ao abrir
  if (checked) {
    setTimeout(() => document.getElementById('inputEmail')?.focus(), 120);
  }
}

// ===================================================================
// 8. ENTRAR NA FILA
// ====================================================================

/**
 * Valida os dados, chama a API para gerar a senha
 * e apresenta o resultado ao utilizador.
 */
async function entrarFila() {
  if (!selectedDept) {
    showToast('⚠️ Escolha um departamento.', 'warning');
    return;
  }

  const prioridade = document.getElementById('tipoSelect')?.value ?? 'verde';
  const email      = document.getElementById('inputEmail')?.value.trim() || null;
  const telefone   = document.getElementById('inputTel')?.value.trim()   || null;

  const btn = document.querySelector('.btn-main'); 
  if (btn) {
    btn.disabled     = true;
    btn.innerHTML    = '⏳ A processar…';
  }

  console.log("SIGF: A tentar entrar na fila...", { departamento: selectedDept, prioridade });

  try {
    const r = await fetch(`${API}/api/queue/join`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        departamento:  selectedDept,
        prioridade,
        email,
        telefone,
        ws_client_id:  wsClientId,
      }),
    });

    if (!r.ok) {
      const msg = await r.text();
      throw new Error(msg || 'Erro do servidor');
    }

    const d = await r.json();
    console.log("SIGF: Senha recebida do servidor:", d);
    currentTicketId = d.ticket_id;
    mostrarResultado(d);
    showToast('✅ Senha gerada com sucesso!', 'success');

  } catch (err) {
    console.error('SIGF entrarFila:', err);
    showToast('❌ Erro ao gerar senha. Verifique a ligação ao servidor.', 'error');
    if (btn) {
      btn.disabled  = false;
      btn.innerHTML = '🎫 Entrar na fila';
    }
  }
}

// ====================================================
// 9. MOSTRAR RESULTADO
// =====================================================

/**
 * Preenche o cartão da senha gerada e faz a transição de ecrã.
 * @param {Object} d - Resposta da API /api/queue/join
 */
function mostrarResultado(d) {
  // Preenche os campos do ticket (Ajustado para os novos IDs)
  setText('rcId',   d.ticket_id);
  setText('rcDept', d.departamento);
  setText('rPos',   d.posicao);

  const tempoEl = document.getElementById('rTempo');
  if (tempoEl) {
    tempoEl.innerHTML = `${d.tempo_estimado_min}<span style="font-size:12px"> min</span>`;
  }

  // Badge de prioridade
  const prioBadge = document.getElementById('rcPrio');
  if (prioBadge) {
    prioBadge.innerHTML = `<span class="rc-prio prio-${d.prioridade}">${PRIO_LABELS[d.prioridade] ?? d.prioridade}</span>`;
  }

  // Transição entre formulário e resultado
  const formSection   = document.getElementById('formSection');
  const resultSection = document.getElementById('resultSection');
  if (formSection)   formSection.style.display   = 'none';
  if (resultSection) {
    resultSection.style.display = 'block'; 
    // Adiciona a classe de animação para garantir que o efeito popIn ocorra
    const card = resultSection.querySelector('.result-ticket-box');
    if (card) card.classList.add('show-anim');
    
    // Scroll suave até ao resultado em mobile
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

/**
 * Utilitário: define textContent de um elemento pelo ID.
 * @param {string} id
 * @param {*} value
 */
function setText(id, value) {
  if (value === undefined || value === null) {
    console.warn(`SIGF: Valor para o ID ${id} está vazio.`);
    return;
  }
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? '–';
}

// ============================================
// 10. DOWNLOAD PDF
// ============================================

/**
 * Abre o PDF da senha gerada numa nova aba.
 */
function downloadPDF() {
  if (!currentTicketId) {
    showToast('⚠️ Nenhuma senha activa.', 'warning');
    return;
  }
  window.open(`${API}/api/ticket/${currentTicketId}/pdf`, '_blank');
}

// =============================================================
// 11. NOVA SENHA — Repõe o formulário
// =============================================================

/**
 * Limpa todo o estado local e repõe a UI para o estado inicial.
 */
function novaSenha() {
  // Limpa estado
  currentTicketId = null;
  selectedDept    = null;

  // Esconde resultado, mostra formulário
  const formSection   = document.getElementById('formSection');
  const resultSection = document.getElementById('resultSection');
  if (formSection)   formSection.style.display   = 'block';
  if (resultSection) {
    resultSection.style.display = 'none';
  }

  // Repõe botões de departamento
  document.getElementById('btnTes')?.classList.remove('selected');
  document.getElementById('btnSec')?.classList.remove('selected');

  // Repõe botão de entrada
  const btnEntrar = document.getElementById('btnEntrar');
  if (btnEntrar) {
    btnEntrar.disabled  = true;
    btnEntrar.innerHTML = '🎫 Entrar na fila';
  }

  // Esconde alertas
  document.getElementById('alert20')?.classList.remove('show');

  // Repõe campos de notificação
  const chk = document.getElementById('chkNotif');
  if (chk) chk.checked = false;
  document.getElementById('notifFields')?.classList.remove('open');
  const emailInput = document.getElementById('inputEmail');
  const telInput   = document.getElementById('inputTel');
  if (emailInput) emailInput.value = '';
  if (telInput)   telInput.value   = '';

  // Scroll para o topo do formulário
  formSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// =============================================
// 12. ALERTA 20 MINUTOS
// =============================================

/**
 * Exibe o banner de alerta de 20 minutos e notifica via toast.
 */
function mostrarAlerta20() {
  const alerta = document.getElementById('alert20');
  if (!alerta) return;
  alerta.classList.add('show');
  notificarSistema('Aviso de Tempo', 'Sua vez está próxima! ~20 minutos restantes.');
}

/**
 * Dispara uma notificação nativa do sistema operacional.
 */
function notificarSistema(titulo, corpo) {
  // Notificação nativa do browser se disponível e autorizada
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(`SIGF: ${titulo}`, {
      body: corpo,
      icon: '/Assets/Imagens/noo.png', // Usando imagem existente no projeto
    });
  }
}

// =====================================================
// 13. TOAST — Sistema de notificações
// =====================================================

/**
 * Mostra uma mensagem de toast.
 * @param {string} msg  - Texto a mostrar
 * @param {string} type - 'success' | 'warning' | 'error'
 * @param {number} ms   - Duração em ms (default 4500)
 */
function showToast(msg, type = 'success', ms = 4500) {
  const t = document.getElementById('toast');
  if (!t) return;

  if (toastTimer) clearTimeout(toastTimer);

  t.textContent = msg;
  t.className   = `toast show ${type}`;

  toastTimer = setTimeout(() => {
    t.classList.remove('show');
    toastTimer = null;
  }, ms);
}

// =========================================
// 14. NAVBAR — Menu mobile
// =========================================

/**
 * Liga o hamburger ao toggle do menu mobile.
 * Previne duplicação de handlers.
 */
function initNavbar() {
  const hamburger = document.querySelector('.hamburger');
  const navLinks  = document.getElementById('navLinks');
  if (!hamburger || !navLinks) return;

  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
  });

  // Fecha ao clicar fora
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove('open');
    }
  });
}

// ======================================================================
// 15. NOTIFICAÇÕES DO BROWSER — Pede permissão ao entrar na fila
// ======================================================================

/**
 * Solicita permissão de notificações nativas após a primeira interacção
 * com os botões de departamento.
 */
function pedirPermissaoNotificacao() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

// ============================================
// 16. INIT — Ponto de entrada
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  conectarWS();
  carregarTiposServico();
  iniciarFallbackHTTP();

  // Pede permissão de notificação ao primeiro clique num departamento
  document.getElementById('btnTes')?.addEventListener('click', pedirPermissaoNotificacao, { once: true });
  document.getElementById('btnSec')?.addEventListener('click', pedirPermissaoNotificacao, { once: true });
});