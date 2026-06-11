/* ============================================================
   SIGF — Sistema Inteligente de Gestão de Filas
   ============================================================ */

'use strict';

// ── Configuração global ───────────────────────────────────────────────────────
const API = window.location.origin;
const POLL_MS = 10_000;   // Intervalo de actualização das stats do hero

// ── Estado da avaliação ───────────────────────────────────────────────────────
let starSelected = 0;

// ===============================================================================
// 1. NAVBAR — Menu mobile e scroll behavior
// ===============================================================================

/**
 * Abre/fecha o menu de navegação mobile.
 * Também anima as três barras do hambúrguer em X.
 */
function toggleMenu() {
  const nav       = document.getElementById('navLinks');
  const hamburger = document.getElementById('hamburger');
  const isOpen    = nav.classList.toggle('open');
  hamburger.classList.toggle('active', isOpen);
}

/* Fecha o menu ao clicar fora dele. */
document.addEventListener('click', (e) => {
  const nav  = document.getElementById('navLinks');
  const ham  = document.getElementById('hamburger');
  if (nav.classList.contains('open') && !nav.contains(e.target) && !ham.contains(e.target)) {
    nav.classList.remove('open');
    ham.classList.remove('active');
  }
});

/* Fecha o menu ao clicar num link de navegação interno. */
document.querySelectorAll('.nav-links a').forEach(link => {
  link.addEventListener('click', () => {
    document.getElementById('navLinks').classList.remove('open');
    document.getElementById('hamburger').classList.remove('active');
  });
});

/* Adiciona sombra extra à navbar ao fazer scroll. */
window.addEventListener('scroll', () => {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;
  navbar.classList.toggle('scrolled', window.scrollY > 20);
});

// ==============================================================================
// 2. HERO — Estatísticas em tempo real
// ===============================================================================

/*
 * Vai buscar ao backend o total de pessoas na fila
 * e actualiza o contador animado no hero.
 */
async function loadHeroStats() {
  try {
    const res  = await fetch(`${API}/api/queue/status`);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    animateCounter('heroFila', data.total_na_fila ?? 0);
  } catch {
    // API offline — mostra hífen sem quebrar a UI
    const el = document.getElementById('heroFila');
    if (el && el.textContent === '–') return;  // Já está a mostrar fallback (solução alternativa)
  }
}

/**
 * Anima um contador numérico de 0 até ao valor final.
 * @param {string} id    - ID do elemento DOM
 * @param {number} target - Valor final
 * @param {number} duration - Duração da animação em ms (default 600)
 */
function animateCounter(id, target, duration = 600) {
  const el = document.getElementById(id);
  if (!el) return;
  const start    = parseInt(el.textContent) || 0;
  const diff     = target - start;
  const steps    = 30;
  const stepTime = duration / steps;
  let   current  = start;
  let   step     = 0;

  const timer = setInterval(() => {
    step++;
    current = Math.round(start + diff * (step / steps));
    el.textContent = current;
    if (step >= steps) {
      clearInterval(timer);
      el.textContent = target;  // Garante O valor exacto no final
    }
  }, stepTime);
}

// Primeira carga imediata + polling periódico
loadHeroStats();
setInterval(loadHeroStats, POLL_MS);

// ── JS do Hero (Ken Burns + carregamento da imagem)
  (function () {
    const bg = document.getElementById('heroBg');
    if (!bg) return;

    const img = new Image();
    img.src = 'img/universidade.jpg';
    img.onload = () => {
      bg.classList.add('loaded');
    };
  })();

// ===========================================================================
// 3. SMOOTH SCROLL — Navegação âncora suave (DESLOCAMENTO SUAVE)
// ============================================================================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    const target = document.querySelector(anchor.getAttribute('href'));
    if (!target) return;
    e.preventDefault();

    const navHeight = document.querySelector('.navbar')?.offsetHeight ?? 68;
    const top = target.getBoundingClientRect().top + window.scrollY - navHeight - 12;

    window.scrollTo({ top, behavior: 'smooth' });
  });
});

// =============================================================================
// 4. OBSERVADOR DE CRUZAMENTOS — Animações de entrada das secções
// =============================================================================

const observerOptions = {
  threshold: 0.12,
  rootMargin: '0px 0px -40px 0px',
};

const appearObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      appearObserver.unobserve(entry.target);  // Só anima uma vez
    }
  });
}, observerOptions);

/** Regista os elementos que devem animar ao entrar no viewport. */
function initScrollAnimations() {
  const targets = document.querySelectorAll(
    '.step-card, .epoch-card, .contacto-item, .feature-card, .stat'
  );
  targets.forEach((el, i) => {
    el.style.transitionDelay = `${i * 60}ms`;
    el.classList.add('fade-up');
    appearObserver.observe(el);
  });
}

// ============================================================================
// 5. AVALIAÇÃO — Modal + estrelas + submissão
// =============================================================================

/** Abre o modal de avaliação. */
function abrirAvaliacao() {
  const modal = document.getElementById('modalAvaliacao');
  if (!modal) return;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';   // Bloqueia scroll do fundo
  // Foco acessível: primeiro elemento interactivo
  setTimeout(() => modal.querySelector('.btn-fechar-modal')?.focus(), 100);
}

/** Fecha o modal de avaliação e repõe o estado. */
function fecharAvaliacao() {
  const modal = document.getElementById('modalAvaliacao');
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

/**
 * Selecciona uma estrela e pinta todas até ela.
 * @param {number} value - Valor de 1 a 5
 */
function selectStar(value) {
  starSelected = value;
  document.querySelectorAll('.star').forEach(star => {
    star.classList.toggle('active', parseInt(star.dataset.v) <= value);
  });
}

/** Hover visual nas estrelas (sem alterar `starSelected`). */
function initStarHover() {
  const stars = document.querySelectorAll('.star');
  stars.forEach(star => {
    star.addEventListener('mouseenter', () => {
      const hoverVal = parseInt(star.dataset.v);
      stars.forEach(s => s.classList.toggle('hover', parseInt(s.dataset.v) <= hoverVal));
    });
    star.addEventListener('mouseleave', () => {
      stars.forEach(s => s.classList.remove('hover'));
    });
  });
}

/** Submete a avaliação — actualmente local, extensível ao backend. */
async function submeterAvaliacao() {
  if (!starSelected) {
    showToast('⚠️ Seleccione pelo menos uma estrela.', 'warning');
    return;
  }

  const comentario = document.getElementById('avaliacaoTexto')?.value.trim() ?? '';

  // Tenta enviar ao backend; falha silenciosamente se offline
  try {
    await fetch(`${API}/api/avaliacao`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estrelas: starSelected, comentario }),
    });
  } catch {
    // API offline — continua o fluxo de UX normalmente
  }

  fecharAvaliacao();
  showToast(`⭐ Obrigado! Avaliação de ${starSelected} estrela(s) registada.`, 'success');

  // Repõe o estado do modal
  starSelected = 0;
  document.querySelectorAll('.star').forEach(s => s.classList.remove('active', 'hover'));
  if (document.getElementById('avaliacaoTexto')) {
    document.getElementById('avaliacaoTexto').value = '';
  }
}

/** Fecha o modal ao clicar no overlay (fora do modal-box). */
document.addEventListener('click', (e) => {
  const overlay = document.getElementById('modalAvaliacao');
  if (e.target === overlay) fecharAvaliacao();
});

/** Fecha o modal com a tecla Escape. */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') fecharAvaliacao();
});

// ==========================================================================
// 6. TOAST — Sistema de notificações
// ==========================================================================

let toastTimer = null;

/**
 * Mostra uma mensagem de toast.
 * @param {string} msg   - Texto a mostrar
 * @param {string} type  - 'success' | 'warning' | 'error'
 * @param {number} ms    - Duração em ms (default 4000)
 */
function showToast(msg, type = 'success', ms = 4000) {
  const toast = document.getElementById('toast');
  if (!toast) return;

  // Cancela timer anterior se existir
  if (toastTimer) clearTimeout(toastTimer);

  toast.textContent = msg;
  toast.className   = `toast show ${type}`;

  toastTimer = setTimeout(() => {
    toast.classList.remove('show');
    toastTimer = null;
  }, ms);
}

// ==========================================================================
// 7. CARTÕES DE ÉPOCAS — Indicador da época académica activa
// ==========================================================================

/**
 * Vai buscar ao backend a época actual e destaca o card correspondente.
 * Não quebra a UI se a API estiver offline.
 */
async function loadEpochStatus() {
  try {
    const res  = await fetch(`${API}/api/queue/status`);
    if (!res.ok) return;
    const data = await res.json();
    const epoch = data.epoch ?? 'normal';

    // Remove destaque de todos os cards
    document.querySelectorAll('.epoch-card').forEach(card => {
      card.classList.remove('epoch-active');
    });

    // Destaca o card da época actual
    const epochMap = { normal: 0, exames: 1, inscricoes: 2 };
    const cards    = document.querySelectorAll('.epoch-card');
    const idx      = epochMap[epoch] ?? 0;
    if (cards[idx]) {
      cards[idx].classList.add('epoch-active');
    }
  } catch {
    // Silencioso
  }
}

// ======================================================================
// 8. SECTION TAG (ETIQUETA DE SECÇÃO) — Animação do subtítulo de secção
// =======================================================================

/**
 * Faz as `.section-tag` aparecerem com delay relativo ao scroll,
 * criando um efeito de cascata com o título abaixo.
 */
function initSectionTags() {
  const tags = document.querySelectorAll('.section-tag');
  const obs  = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  tags.forEach(tag => {
    tag.classList.add('tag-hidden');
    obs.observe(tag);
  });
}

// ==============================================================================
// 9. ACTIVA O NAV LINK — Destaca o link correspondente à secção visível
// ==============================================================================

function initActiveNavHighlight() {
  const sections = document.querySelectorAll('section[id]');
  const links    = document.querySelectorAll('.nav-links a[href^="#"]');

  if (!sections.length || !links.length) return;

  const navObs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const id = entry.target.id;
      links.forEach(link => {
        link.classList.toggle(
          'nav-active',
          link.getAttribute('href') === `#${id}`
        );
      });
    });
  }, { threshold: 0.45, rootMargin: '-60px 0px -40% 0px' });

  sections.forEach(s => navObs.observe(s));
}

// ========================================================================
// 10. ACESSIBILIDADE — Suporte a teclado nas estrelas e no modal
// ========================================================================

function initStarKeyboard() {
  document.querySelectorAll('.star').forEach(star => {
    star.setAttribute('role', 'button');
    star.setAttribute('tabindex', '0');
    star.setAttribute('aria-label', `${star.dataset.v} estrela${star.dataset.v > 1 ? 's' : ''}`);
    star.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectStar(parseInt(star.dataset.v));
      }
    });
  });
}

// ==============================================================================
// 11. INIT — Ponto de entrada da aplicação
// ===============================================================================

document.addEventListener('DOMContentLoaded', () => {
  initScrollAnimations();
  initSectionTags();
  initActiveNavHighlight();
  initStarHover();
  initStarKeyboard();
  loadEpochStatus();
});