// ── Utilities ────────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
}

// Close sidebar on backdrop click (mobile)
document.addEventListener('click', e => {
  const sidebar = document.querySelector('.sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  if (sidebar && sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) && !toggle.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// ── Toast Notifications ───────────────────────────────────────────────────────

function showToast(message, type = 'info', duration = 4000) {
  const container = $('toast-container');
  if (!container) return;

  const icons = {
    success: '✓',
    error: '✕',
    info: 'ℹ',
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span style="font-size:15px;flex-shrink:0">${icons[type] || icons.info}</span>
    <span style="flex:1">${escapeHtml(message)}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── API Helper ─────────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.error('API error:', e);
    throw e;
  }
}

// ── Scrape Status Polling ─────────────────────────────────────────────────────

let _statusInterval = null;

function startStatusPolling() {
  if (_statusInterval) return;
  _statusInterval = setInterval(pollScrapeStatus, 2000);
  pollScrapeStatus();
}

async function pollScrapeStatus() {
  try {
    const data = await apiFetch('/api/scrape/status');
    updateScrapeUI(data);
    if (!data.running && _statusInterval) {
      clearInterval(_statusInterval);
      _statusInterval = null;
      if (data.last_result) {
        const r = data.last_result;
        showToast(`Scrape complete — ${r.leads_added} new leads found`, 'success', 6000);
        if (typeof refreshDashboard === 'function') refreshDashboard();
        if (typeof loadLeads === 'function') loadLeads();
      }
    }
  } catch (e) {
    // Silent fail on polling errors
  }
}

function updateScrapeUI(data) {
  const dot = $('scrape-status-indicator');
  const text = $('scrape-status-text');
  const progressContainer = $('progress-container');
  const progressBar = $('progress-bar');
  const progressMsg = $('progress-message');

  if (!dot) return;

  if (data.running) {
    dot.className = 'status-dot status-running';
    if (text) text.textContent = 'Scraping...';
    if (progressContainer) {
      progressContainer.classList.remove('hidden');
      // The progress bar is inside a track wrapper
      const track = progressContainer.querySelector('.progress-bar-track');
      if (track && progressBar) {
        progressBar.style.width = (data.progress || 0) + '%';
      } else if (progressBar) {
        progressBar.style.width = (data.progress || 0) + '%';
      }
    }
    if (progressMsg) progressMsg.textContent = data.message || '';
  } else {
    dot.className = 'status-dot status-idle';
    if (text) text.textContent = 'Ready';
    if (progressContainer) progressContainer.classList.add('hidden');
  }
}

// ── Start Scrape ──────────────────────────────────────────────────────────────

async function startScrape(sources) {
  try {
    const btn = $('start-scrape-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Starting...';
    }

    await apiFetch('/api/scrape/start', {
      method: 'POST',
      body: JSON.stringify({ sources: sources || ['google', 'directories', 'linkedin', 'instagram'] }),
    });

    showToast('Scrape started — this may take several minutes', 'info');
    startStatusPolling();
  } catch (e) {
    showToast(`Failed to start scrape: ${e.message}`, 'error');
    const btn = $('start-scrape-btn');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg> Start Scrape Now';
    }
  }
}

// ── Badge Helpers ─────────────────────────────────────────────────────────────

function statusBadge(status) {
  const map = {
    'New': 'badge-new',
    'Contacted': 'badge-contacted',
    'Replied': 'badge-replied',
    'Call Booked': 'badge-call',
    'Closed': 'badge-closed',
    'Not Qualified': 'badge-disqualified',
  };
  const cls = map[status] || 'badge-disqualified';
  return `<span class="badge ${cls}">${escapeHtml(status || 'New')}</span>`;
}

function sourceBadge(source) {
  const s = (source || '').toLowerCase();
  let cls = 'source-directories';
  let label = source || 'unknown';
  if (s.includes('google')) { cls = 'source-google'; label = 'Google'; }
  else if (s.includes('instagram')) { cls = 'source-instagram'; label = 'Instagram'; }
  else if (s.includes('linkedin')) { cls = 'source-linkedin'; label = 'LinkedIn'; }
  else if (s.includes('noomii') || s.includes('bark') || s.includes('coach')) { cls = 'source-directories'; label = 'Directory'; }
  return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function scoreDots(score, max = 10) {
  const filled = Math.min(score, max);
  let dots = '';
  for (let i = 0; i < 5; i++) {
    dots += `<span class="score-dot ${i < Math.round(filled/2) ? 'filled' : ''}"></span>`;
  }
  return `<div class="score-bar"><div class="score-dots">${dots}</div><span class="score-num">${score}</span></div>`;
}

function formatDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Countdown Timer ───────────────────────────────────────────────────────────

function startCountdown(nextRunEl, nextTimeStr) {
  if (!nextRunEl || !nextTimeStr) return;

  function update() {
    const diff = new Date(nextTimeStr) - new Date();
    if (diff <= 0) {
      nextRunEl.textContent = 'Imminent';
      return;
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    nextRunEl.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }

  update();
  setInterval(update, 1000);
}

// ── On Load ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Check if a scrape is currently running
  pollScrapeStatus().then(() => {
    const dot = $('scrape-status-indicator');
    if (dot && dot.classList.contains('status-running')) {
      startStatusPolling();
    }
  });
});
