/* ─── CONFIGURAÇÃO DO SERVIDOR E ENDEREÇO ────────────────────────────────────────── */
const API = window.location.origin;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/painel`;

/* ─── ESTADO DO PERFIL ───────────────────────────────────────────── */
const STATE = {
  filas:     { Tesouraria: [], Secretaria: [] },
  historico: [],
  gestores:  [],
  online:    true,
  connOn:    true,
  filterDept: 'Todos',
  searchTerm: '',
  user:      null,
  epoch:     'normal'
};

/* Gestores padrão */
const GESTORES_DEFAULT = [
  { id:'admin',      nome:'Administrador',      papel:'admin',  dept:null,         estado:'Ativo', online:true, foto:'/Assets/Imagens/admin.png' },
  { id:'tesouraria', nome:'Gestor Tesouraria',  papel:'gestor', dept:'Tesouraria', estado:'Ativo', online:true, foto:'/Assets/Imagens/gestor_t.png' },
  { id:'secretaria', nome:'Gestor Secretaria',  papel:'gestor', dept:'Secretaria', estado:'Ativo', online:true, foto:'/Assets/Imagens/gestor_s.png' },
];

/* ─── AUTENTICAÇÃO (Login) ───────────────────────────────────────── */
async function executarLogin() {
  const username = document.getElementById('userIn').value;
  const password = document.getElementById('passIn').value;
  const errorEl  = document.getElementById('loginError');

  try {
    const r = await fetch(`${API}/api/login`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ username, password })
    });

    if (!r.ok) throw new Error();
    
    const user = await r.json();
    localStorage.setItem('sigf_user', JSON.stringify(user));
    location.reload(); // Recarrega para aplicar permissões
  } catch (e) {
    errorEl.style.display = 'block';
    setTimeout(() => { errorEl.style.display = 'none'; }, 3000);
  }
}

async function changeEpoch(newEpoch) {
  if (STATE.user?.papel !== 'admin') {
    showToast('Apenas o Administrador pode alterar a época.', 'error');
    return;
  }
  try {
    const r = await fetch(`${API}/api/admin/set-epoch`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ epoch: newEpoch })
    });
    if (!r.ok) throw new Error();
    showToast(`Período alterado para: ${newEpoch}`, 'info');
  } catch (e) {
    showToast('Erro ao alterar período académico', 'error');
  }
}

function logout() {
  localStorage.removeItem('sigf_user');
  location.reload();
}

function checkAuth() {
  const saved = localStorage.getItem('sigf_user');
  if (saved) {
    STATE.user = JSON.parse(saved);
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('userName').textContent = STATE.user.nome;
    document.querySelector('.profile-role').textContent = `${STATE.user.papel} · ${STATE.user.dept || 'Geral'}`;

    // Actualizar a foto do perfil na sidebar e na topbar
    const avatars = [document.getElementById('userAvatar'), document.getElementById('topbarAvatar')];
    avatars.forEach(avatarDiv => {
      if (!avatarDiv) return;
      if (STATE.user.foto) {
        avatarDiv.innerHTML = `<img src="${STATE.user.foto}" alt="Perfil"><span class="status-dot"></span>`;
      } else {
        const inicial = (STATE.user.nome || 'U').charAt(0).toUpperCase();
        avatarDiv.innerHTML = `${inicial}<span class="status-dot"></span>`;
      }
    });
    
    // Restrição de privilégios: Apenas admin vê a aba de Membros (como combinado)
    if (STATE.user.papel !== 'admin') {
      const membrosTab = document.querySelector('[data-sec="membros"]');
      if (membrosTab) membrosTab.style.display = 'none';
      
      const epocasTab = document.querySelector('[data-sec="epocas"]');
      if (epocasTab) epocasTab.style.display = 'none';
    } else {
      // Mostra o controlo de época apenas para o Admin
      const epochCtrl = document.getElementById('adminEpochControl');
      if (epochCtrl) epochCtrl.style.display = 'flex';
    }
  }
}

/* ── GESTÃO DE FOTO DE PERFIL (Alteração da Foto de Perfil) ────────────────────────────── */
function triggerFotoUpload() {
  const input = document.getElementById('fotoInput');
  if (input) input.click();
}

function handleFotoUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Limite de 2MB para LocalStorage (A foto não pesar muito tipo aplicativo, rsrsrs)
  if (file.size > 2 * 1024 * 1024) {
    showToast('A imagem deve ter menos de 2MB', 'error');
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const base64Image = e.target.result;
    STATE.user.foto = base64Image;
    localStorage.setItem('sigf_user', JSON.stringify(STATE.user));
    checkAuth();
    showToast('Foto de perfil atualizada!', 'success');
  };
  event.target.value = ''; 
  reader.readAsDataURL(file);
}

/* ─── NAVEGAÇÃO (Menu de Navegação a esquerda do painel) ────────────────────────────────────────── */
const SECTION_TITLES = { chamadas:'Visão Geral', senhas:'Senhas na Fila', chamar:'Chamar Senha', membros:'Membros', epocas:'Gestão de Épocas' };

function navTo(id, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-'+id).classList.add('active');
  if (el) el.classList.add('active');
  document.getElementById('topbarHeading').textContent = SECTION_TITLES[id] || id;
}

/* ─── RELÓGIO (Não era necessário, mas decidi colocar)──────────────────────────────────────────── */
function updateClock(){
  const n = new Date();
  document.getElementById('topbarClock').textContent =
    n.getHours().toString().padStart(2,'0') + ':' +
    n.getMinutes().toString().padStart(2,'0') + ':' +
    n.getSeconds().toString().padStart(2,'0');
}
setInterval(updateClock, 1000); updateClock();

/* ─── TOGGLE ONLINE (sidebar, Aqui é mesmo só para alternar entre onine e offline) ──────────────────────────── */
function toggleOnline() {
  STATE.online = !STATE.online;
  const btn   = document.getElementById('toggleBtn');
  const label = document.getElementById('toggleLabel');
  btn.classList.toggle('offline', !STATE.online);
  label.textContent = STATE.online ? 'Online' : 'Offline';
  showToast(STATE.online ? 'Estado: Online ✅' : 'Estado: Offline ❌', STATE.online ? 'success' : 'error');
}

/* ─── TOGGLE CONECTADO (card, para alternar entre conectado e desconectado) ──────────────────────────── */
function toggleConn() {
  STATE.connOn = !STATE.connOn;
  const block  = document.getElementById('connBlock');
  const toggle = document.getElementById('connToggle');
  const label  = document.getElementById('connLabel');
  block.classList.toggle('off',  !STATE.connOn);
  toggle.classList.toggle('off', !STATE.connOn);
  label.textContent = STATE.connOn
    ? 'Clique para alternar o status entre Conectado ou Desconectado.'
    : 'Você está DESCONECTADO. Clique para ligar.';
}

/* ─── WEBSOCKET (Aqui é simplesmente para a comunicação entre navegador e servidor em tempo real, os itens a serem actualizados)────────────────────────────────────────── */
let ws;
function conectarWS() {
  try { ws = new WebSocket(WS_URL); } catch(e){ setWSStatus(false); return; }

  ws.onopen = () => setWSStatus(true);

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.tipo === 'estado_fila')  aplicarEstado(msg);
      if (msg.tipo === 'senha_chamada') onSenhaChamada(msg);
    } catch(e2){}
  };

  ws.onclose = () => { setWSStatus(false); setTimeout(conectarWS, 3000); };
  ws.onerror = () => ws.close();
}

function setWSStatus(on) {
  const pill  = document.getElementById('wsPill');
  const dot   = document.getElementById('wsDot');
  const label = document.getElementById('wsLabel');
  pill.classList.toggle('off', !on);
  dot.style.background  = on ? 'var(--green)' : 'var(--red)';
  label.textContent     = on ? 'Em tempo real' : 'Desligado — a reconectar…';
}

/* ─── APLICAR ESTADO ───────────────────────────────────── */
function aplicarEstado(data) {
  // Suporta tanto payload directo (`/api/estado`) como mensagem WS com { tipo, dados }
  const payload = data.dados || data || {};
  const filas    = payload.filas || {};
  const T = filas['Tesouraria'] || { total:0, tempo_medio:8, senhas:[] };
  const S = filas['Secretaria'] || { total:0, tempo_medio:12, senhas:[] };

  STATE.filas['Tesouraria'] = T.senhas || [];
  STATE.filas['Secretaria'] = S.senhas || [];

  /* KPIs (Aqui são as métricas)*/
  const total = (T.total||0) + (S.total||0);
  document.getElementById('kpiTotalFila').textContent   = total;
  document.getElementById('kpiAguardam').textContent    = total;

  // Actualizar UI de épocas (Tá claro)
  if (data.epoch) {
    STATE.epoch = data.epoch;
    ['normal', 'exames', 'inscricoes'].forEach(ep => {
      const card = document.getElementById(`card-epoch-${ep}`);
      const btn = document.getElementById(`btn-epoch-${ep}`);
      const status = document.getElementById(`status-${ep}`);
      if (card && btn && status) {
        const isActive = STATE.epoch === ep;
        card.classList.toggle('active', isActive);
        status.textContent = isActive ? '● Activo Agora' : 'Inactivo';
        btn.textContent = isActive ? 'Período Activo' : 'Ativar Período';
        btn.disabled = isActive;
      }
    });
  }
  document.getElementById('kpiChamadas').textContent    = data.total_chamadas_hoje || STATE.historico.length;
  document.getElementById('navBadge').textContent       = total;

  /* Barras */
  const maxBar = Math.max(total, 1);
  document.getElementById('barValT').textContent  = T.total||0;
  document.getElementById('barValS').textContent  = S.total||0;
  document.getElementById('barFillT').style.width = Math.round(((T.total||0)/maxBar)*100) + '%';
  document.getElementById('barFillS').style.width = Math.round(((S.total||0)/maxBar)*100) + '%';
  document.getElementById('barTempoT').textContent = (T.tempo_medio||8) + ' min';
  document.getElementById('barTempoS').textContent = (S.tempo_medio||12) + ' min';

  /* Chamar section */
  document.getElementById('chamarNumT').textContent = T.total||0;
  document.getElementById('chamarNumS').textContent = S.total||0;
  const pT = T.senhas && T.senhas.length ? T.senhas[0].id : '–';
  const pS = S.senhas && S.senhas.length ? S.senhas[0].id : '–';
  document.getElementById('proximaT').textContent = pT;
  document.getElementById('proximaS').textContent = pS;
  document.getElementById('btnChamarT').disabled = !T.total;
  document.getElementById('btnChamarS').disabled = !S.total;

  /* Gestores */
  if (data.gestores && data.gestores.length) {
    STATE.gestores = data.gestores;
    renderMembros(data.gestores);
  }

  /* Tabela */
  renderSenhasTable();
}

/* ─── CHAMAR A PRÓXIMA SENHA ────────── */
async function chamarProxima() {
  const dept = document.getElementById('deptSelect').value;
  await chamarDept(dept);
}

/* ─── CHAMAR POR DEPT ──────────────────────────────────── */
async function chamarDept(dept) {
  try {
    const r = await fetch(`${API}/api/chamar`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ dept })
    });
    if (!r.ok) throw new Error();
    const d = await r.json();
    onSenhaChamada({ senha: d.chamada, dept });
  } catch(e) {
    /* Simulação offline */
    const fila = STATE.filas[dept];
    if (!fila || !fila.length) { showToast('Fila de ' + dept + ' está vazia.', 'warning'); return; }
    const senha = fila.shift();
    STATE.historico.unshift({ ...senha, hora_chamada: new Date().toISOString() });
    STATE.filas[dept] = fila;
    onSenhaChamada({ senha, dept });
    /* Actualiza KPIs localmente */
    const total = STATE.filas['Tesouraria'].length + STATE.filas['Secretaria'].length;
    document.getElementById('kpiTotalFila').textContent  = total;
    document.getElementById('kpiAguardam').textContent   = total;
    document.getElementById('kpiChamadas').textContent   = STATE.historico.length;
    document.getElementById('navBadge').textContent      = total;
    renderSenhasTable();
    renderHistorico();
  }
}

function onSenhaChamada(msg) {
  const senha = msg.senha || msg;
  const dept  = msg.dept || senha.dept;

  const isT = dept === 'Tesouraria';
  const dispId = isT ? 'chamadaT' : 'chamadaS';
  const dispEl = document.getElementById(dispId);
  document.getElementById(isT ? 'chamadaIdT' : 'chamadaIdS').textContent = senha.id;
  dispEl.style.display = 'block';

  /* Última chamada nas barras */
  document.getElementById(isT ? 'barUltimaT' : 'barUltimaS').textContent = senha.id;

  showToast('📢 ' + senha.id + ' — ' + dept + ' chamada!', 'success');

  /* Histórico */
  if (!STATE.historico.find(h => h.id === senha.id)) {
    STATE.historico.unshift({ ...senha, hora_chamada: new Date().toISOString() });
  }
  renderHistorico();

  setTimeout(() => { dispEl.style.display = 'none'; }, 8000);
}

/* ─── RENDER TABELA SENHAS ─────────────────────────────── */
function renderSenhasTable() {
  const tbody = document.getElementById('senhasTableBody');
  let todas = [
    ...STATE.filas['Tesouraria'].map(s => ({...s, dept:'Tesouraria'})),
    ...STATE.filas['Secretaria'].map(s => ({...s, dept:'Secretaria'})),
  ];

  if (STATE.filterDept !== 'Todos') todas = todas.filter(s => s.dept === STATE.filterDept);
  if (STATE.searchTerm) todas = todas.filter(s => String(s.id).toLowerCase().includes(STATE.searchTerm.toLowerCase()));

  if (!todas.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Nenhuma senha encontrada.</td></tr>';
    return;
  }

  tbody.innerHTML = todas.map(s => {
    const dt = new Date(s.data_hora || Date.now());
    const data = dt.toLocaleDateString('pt-PT');
    const isT = s.dept === 'Tesouraria';
    return `
    <tr>
      <td><span class="td-senha">${s.id}</span></td>
      <td><span class="badge-dept ${isT?'t':'s'}">${isT?'💰':'📚'} ${s.dept}</span></td>
      <td><span style="font-size:.78rem;color:var(--grey-500)">Serviço Geral</span></td>
      <td><span class="badge-estado">Na fila</span></td>
      <td><span style="font-size:.78rem;color:var(--grey-400);font-family:var(--mono)">${data}</span></td>
      <td>
        <button class="btn-aviao" title="Reemitir / Suporte" onclick="suporteSenha('${s.id}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
        </button>
      </td>
    </tr>`;
  }).join('');
}

function filterSenhas(dept, btn) {
  STATE.filterDept = dept;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderSenhasTable();
}
function searchSenhas(val) { STATE.searchTerm = val; renderSenhasTable(); }
function suporteSenha(id) { showToast('Suporte enviado para a senha ' + id + ' ✈', 'info'); }

/* ─── RENDER HISTÓRICO ─────────────────────────────────── */
function renderHistorico() {
  const el = document.getElementById('historicoList');
  document.getElementById('historicoCount').textContent = STATE.historico.length + ' hoje';
  document.getElementById('kpiChamadas').textContent   = STATE.historico.length;

  if (!STATE.historico.length) {
    el.innerHTML = '<div style="text-align:center;padding:28px;color:var(--grey-400);font-size:.8rem">Nenhuma chamada ainda.</div>';
    return;
  }
  el.innerHTML = STATE.historico.slice(0, 8).map(h => {
    const hora = h.hora_chamada ? new Date(h.hora_chamada).toLocaleTimeString('pt-PT', {hour:'2-digit',minute:'2-digit'}) : '–';
    const isT  = h.dept === 'Tesouraria';
    return `
    <div class="hist-item">
      <div class="hist-dot" style="background:${isT?'var(--teal)':'var(--orange)'}"></div>
      <div class="hist-id">${h.id}</div>
      <div class="hist-dept">${h.dept}</div>
      <div class="hist-hora">${hora}</div>
    </div>`;
  }).join('');
}

/* ─── RENDER MEMBROS ───────────────────────────────────── */
function renderMembros(gestores) {
  const grid = document.getElementById('membrosGrid');
  document.getElementById('membrosCount').textContent = gestores.length + ' Membros';

  grid.innerHTML = gestores.map(g => {
    const imgContent = g.foto 
      ? `<img src="${g.foto}" alt="${g.nome}" onerror="this.src='';this.parentElement.textContent='${g.nome.charAt(0)}'">` 
      : (g.nome || 'G').charAt(0).toUpperCase();
      
    const cls = {
      'Ativo':'ativo','Descanso':'descanso','Desativado':'desativado'
    }[g.estado] || 'desativado';
    const estCls = {
      'Ativo':'estado-ativo','Descanso':'estado-descanso','Desativado':'estado-desativado'
    }[g.estado] || 'estado-desativado';
    return `
    <div class="membro-card" onclick="toggleMembroEstado('${g.id}')">
      <div class="membro-avatar ${cls}">
        ${imgContent}
        <span class="membro-online ${g.online?'on':'off'}"></span>
      </div>
      <div class="membro-nome">${g.nome}</div>
      <div class="membro-estado ${estCls}">${g.estado}</div>
    </div>`;
  }).join('');
}

function toggleMembroEstado(id) {
  const g = STATE.gestores.find(m => m.id === id);
  if (!g) return;
  const estados = ['Ativo','Descanso','Desativado'];
  const i = estados.indexOf(g.estado);
  g.estado = estados[(i+1) % estados.length];
  g.online = g.estado === 'Ativo';
  renderMembros(STATE.gestores);
  showToast(g.nome + ' → ' + g.estado, 'info');
  /* Chamar API */
  fetch(`${API}/api/gestor/toggle`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gestor_id:id})}).catch(()=>{});
}

/* ─── TOAST (Brinde) ────────────────────────────────────────────── */
const toastIcons = { success:'✅', error:'❌', info:'ℹ️', warning:'⚠️' };
let toastTimer;
function showToast(msg, type='success') {
  const t   = document.getElementById('toast');
  const ico = document.getElementById('toast').querySelector('.toast-icon');
  document.getElementById('toastMsg').textContent = msg;
  ico.textContent = toastIcons[type] || '•';
  t.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 4500);
}

/* ─── INIT (é só para inicializar) ─────────────────────────────────────────────── */
function init() {
  /* Verifica o login primeiro */
  checkAuth();

  // Suporte ao Enter no login
  const passIn = document.getElementById('passIn');
  if (passIn) {
    passIn.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') executarLogin();
    });
  }

  if (!STATE.user) return;

  /* Carrega os gestores padrão */
  STATE.gestores = [...GESTORES_DEFAULT];
  renderMembros(STATE.gestores);

  /* Tenta ligar ao servidor */
  conectarWS();

  /* Fallback: carrega estado via REST */
  fetch(`${API}/api/estado`)
    .then(r => r.json())
    .then(d => aplicarEstado(d))
    .catch(() => {
      /* Modo demo: popula com dados fictícios */
      setTimeout(populateDemo, 500);
    });
}

/* ─── DADOS DEMO (quando API está offline) ─────────────────── */
function populateDemo() {
  const DEMO = {
    tipo: 'estado_fila',
    filas: {
      Tesouraria: {
        total: 7, tempo_medio: 8,
        senhas: [
          {id:'T-0001',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0002',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0003',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0004',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0005',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0006',dept:'Tesouraria',data_hora:new Date().toISOString()},
          {id:'T-0007',dept:'Tesouraria',data_hora:new Date().toISOString()},
        ]
      },
      Secretaria: {
        total: 11, tempo_medio: 12,
        senhas: [
          {id:'S-0001',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0002',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0003',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0004',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0005',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0006',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0007',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0008',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0009',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0010',dept:'Secretaria',data_hora:new Date().toISOString()},
          {id:'S-0011',dept:'Secretaria',data_hora:new Date().toISOString()},
        ]
      }
    },
    
    total_chamadas_hoje: 13,
    gestores: GESTORES_DEFAULT
  };
  aplicarEstado(DEMO);
  setWSStatus(false);
  showToast('Modo demo — API offline', 'warning');
}

init();