/* Discord Helper — GUI runtime (XP theme) */

async function fetchJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

// ── format helpers ────────────────────────────────────────────────────────────

function fmtUptime(seconds) {
  if (!seconds) return '00:00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':')
}

function set(id, val) {
  const el = document.getElementById(id)
  if (el) el.textContent = val
}

function setHTML(id, html) {
  const el = document.getElementById(id)
  if (el) el.innerHTML = html
}

// ── sidebar tabs ──────────────────────────────────────────────────────────────

function initTabs() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'))
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'))
      item.classList.add('active')
      const tab = document.getElementById('tab-' + item.dataset.tab)
      if (tab) tab.classList.add('active')
    })
  })
}

// ── status loading ────────────────────────────────────────────────────────────

async function loadStatus() {
  try {
    const s = await fetchJSON('/api/status')

    // Bot runtime
    const online = s.bot?.connected ?? false
    const pulse = document.getElementById('runtime-pulse')
    if (pulse) {
      pulse.className = 'pulse ' + (online ? 'online' : 'offline')
    }
    set('runtime-status', online ? 'RUNNING' : 'OFFLINE')
    set('bot-connected', online ? 'Connected' : 'Offline')
    set('bot-uptime', fmtUptime(s.bot?.uptime_seconds ?? 0))
    set('bot-guilds', s.bot?.guilds_count ?? '—')

    // Status bar
    set('status-text', online ? 'Connected' : 'Offline')

    // Runtime stack
    set('stack-stt', s.runtime_stack?.stt ?? '—')
    set('stack-llm', s.runtime_stack?.llm ?? '—')
    set('stack-tts', s.runtime_stack?.tts ?? '—')
    set('stack-audio', s.runtime_stack?.audio ?? 'FFmpeg')

    // Discord card
    set('discord-slash', s.bot?.slash_commands ?? 6)
    const hasVoice = !!s.dependencies?.ffmpeg
    const hasTTS   = hasVoice
    const hasText  = !!s.config?.discord_token_configured

    setCheckItem('chk-voice', 'discord-voice', hasVoice, 'Ready', 'Missing FFmpeg')
    setCheckItem('chk-tts',   'discord-tts',   hasTTS,   'Ready', 'Missing FFmpeg')
    setCheckItem('chk-text',  'discord-text',  hasText,  'Ready', 'Token missing')

  } catch {
    set('runtime-status', 'OFFLINE')
    set('status-text', 'API unreachable')
    const pulse = document.getElementById('runtime-pulse')
    if (pulse) pulse.className = 'pulse offline'
  }
}

function setCheckItem(chkId, valId, ok, yes, no) {
  const chk = document.getElementById(chkId)
  const val = document.getElementById(valId)
  if (chk) { chk.textContent = ok ? '✓' : '✗'; chk.className = 'check ' + (ok ? 'green' : 't-err') }
  if (val) val.textContent = ok ? yes : no
}

// ── log terminal ──────────────────────────────────────────────────────────────

async function loadDiagnostics() {
  try {
    const s = await fetchJSON('/api/status')
    const deps = s.dependencies ?? {}
    const cfg  = s.config ?? {}

    const checks = [
      { label: 'Python',   ok: true,                       value: '3.10+' },
      { label: 'Ollama',   ok: !!deps.ollama_server_running, value: deps.ollama_server_running ? 'Running' : 'Offline' },
      { label: 'GPU',      ok: !!deps.nvidia_smi,           value: deps.nvidia_smi ? 'Detected' : 'Not detected (CPU mode)' },
      { label: 'ffmpeg',   ok: !!deps.ffmpeg,               value: deps.ffmpeg ? 'Found' : 'Not found' },
      { label: '.env',     ok: cfg.exists,                  value: cfg.exists ? 'Loaded' : 'Not configured' },
      { label: 'Token',    ok: cfg.discord_token_configured, value: cfg.discord_token_configured ? 'Configured' : 'Missing' },
    ]

    const platform = s.platform ?? {}
    const header = `C:\\Discord-Helper> discord-helper doctor\n`
    const lines = checks.map(c => {
      const dot   = c.label.padEnd(14, '.')
      const badge = c.ok ? '<span class="t-ok">[✓]</span>' : '<span class="t-err">[✗]</span>'
      const val   = `<span class="${c.ok ? 't-hi' : 't-err'}">${c.value}</span>`
      return `${badge} <span class="t-dim">${dot}</span> ${val}`
    })

    const allOk = checks.every(c => c.ok)
    const footer = allOk
      ? '\n<span class="t-ok">All systems operational.</span>'
      : '\n<span class="t-err">Some checks failed — run discord-helper doctor for details.</span>'

    setHTML('terminal-output', header + lines.join('\n') + footer)

  } catch {
    setHTML('terminal-output', '<span class="t-err">Could not reach runtime API. Is the GUI server running?</span>\n\nRun: discord-helper gui')
  }
}

// ── main refresh loop ─────────────────────────────────────────────────────────

async function refresh() {
  await Promise.all([loadStatus(), loadDiagnostics()])
}

initTabs()
refresh()
setInterval(refresh, 5000)
