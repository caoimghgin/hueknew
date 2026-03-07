"""Self-contained HTML dashboard page.

Returns a complete HTML document as a Python string — all CSS and JS inline.
No external dependencies, no build toolchain, no CDN imports.
Charts rendered with Canvas 2D API.
"""


def render_dashboard_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chromatic Census</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --orange: #d29922;
    --red: #f85149;
    --jnd-color: #58a6ff;
    --accept-color: #d29922;
    --obvious-color: #3fb950;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 24px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
  }
  header h1 { font-size: 24px; font-weight: 600; }
  header .subtitle { color: var(--text-dim); font-size: 14px; }
  #connection-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 12px;
    background: var(--green);
    color: #000;
  }
  #connection-status.error { background: var(--red); color: #fff; }

  nav.views {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }
  nav.views a {
    color: var(--text-dim);
    text-decoration: none;
    font-size: 13px;
    padding: 4px 12px;
    border: 1px solid var(--border);
    border-radius: 16px;
    transition: all 0.15s ease;
  }
  nav.views a:hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .grid { display: grid; gap: 16px; margin-bottom: 16px; }
  .grid-3 { grid-template-columns: repeat(3, 1fr); }
  .grid-2 { grid-template-columns: 1fr 1fr; }
  .grid-12 { grid-template-columns: 2fr 1fr; }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }
  .card h3 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    margin-bottom: 8px;
  }

  /* Progress bar */
  .progress-bar {
    width: 100%;
    height: 8px;
    background: var(--border);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 12px;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--green));
    border-radius: 4px;
    transition: width 0.5s ease;
  }
  .progress-stats {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: var(--text-dim);
  }
  .progress-stats span { white-space: nowrap; }

  /* Tier count cards */
  .tier-card { text-align: center; }
  .tier-card .count {
    font-size: 36px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
  }
  .tier-card .rate {
    font-size: 13px;
    color: var(--text-dim);
    margin-top: 4px;
  }
  .tier-card .delta {
    font-size: 12px;
    color: var(--text-dim);
  }
  .tier-jnd .count { color: var(--jnd-color); }
  .tier-accept .count { color: var(--accept-color); }
  .tier-obvious .count { color: var(--obvious-color); }

  /* Color of the moment */
  .color-moment {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .color-swatch {
    width: 80px;
    height: 80px;
    border-radius: 8px;
    border: 2px solid var(--border);
    flex-shrink: 0;
  }
  .color-info {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.8;
  }
  .color-info .hex { font-size: 20px; font-weight: 600; }

  /* Charts */
  canvas { width: 100%; height: 200px; display: block; }
  .chart-tall canvas { height: 300px; }

  /* Color strip */
  #strip-canvas { height: 60px; border-radius: 4px; }

  /* Run log */
  .log-entries {
    font-family: 'SF Mono', 'Cascadia Code', monospace;
    font-size: 12px;
    max-height: 200px;
    overflow-y: auto;
    color: var(--text-dim);
  }
  .log-entries div { padding: 2px 0; border-bottom: 1px solid var(--border); }
  .log-entries .event { color: var(--accent); }

  /* Practical stats */
  .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 13px;
  }
  .stat-row .label { color: var(--text-dim); }

  .not-started {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 18px;
  }

  @media (max-width: 800px) {
    .grid-3 { grid-template-columns: 1fr; }
    .grid-2, .grid-12 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>Chromatic Census</h1>
    <span class="subtitle">Enumerating human-distinguishable colors</span>
  </div>
  <span id="connection-status">Connecting...</span>
</header>

<nav class="views">
  <a href="/jnd-audit">JND Visual Audit</a>
  <a href="/jnd-neighborhood">JND Neighborhood</a>
  <a href="/jnd-graph">JND Graph</a>
</nav>

<div id="app">
  <div class="not-started" id="not-started">
    Waiting for census to start...
  </div>

  <div id="dashboard" style="display:none">
    <!-- Progress -->
    <div class="card" style="margin-bottom:16px">
      <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
      <div class="progress-stats">
        <span id="stat-slice">Slice 0/0</span>
        <span id="stat-L">L* = 0.00</span>
        <span id="stat-elapsed">Elapsed: --</span>
        <span id="stat-eta">ETA: --</span>
        <span id="stat-rate">0 pts/sec</span>
      </div>
    </div>

    <!-- Tier counts -->
    <div class="grid grid-3">
      <div class="card tier-card tier-jnd">
        <h3>JND</h3>
        <div class="delta">&Delta;E = 1.0</div>
        <div class="count" id="count-jnd">0</div>
        <div class="rate" id="rate-jnd">Theoretical limit</div>
      </div>
      <div class="card tier-card tier-accept">
        <h3>Acceptability</h3>
        <div class="delta">&Delta;E = 2.0</div>
        <div class="count" id="count-accept">0</div>
        <div class="rate" id="rate-accept">Meaningfully different</div>
      </div>
      <div class="card tier-card tier-obvious">
        <h3>Obvious</h3>
        <div class="delta">&Delta;E = 5.0</div>
        <div class="count" id="count-obvious">0</div>
        <div class="rate" id="rate-obvious">Obviously different</div>
      </div>
    </div>

    <!-- Color strip + Color of the moment -->
    <div class="grid grid-12" style="margin-top:16px">
      <div class="card">
        <h3>Color Strip &mdash; Completed L* Slices</h3>
        <canvas id="strip-canvas"></canvas>
      </div>
      <div class="card">
        <h3>Color of the Moment</h3>
        <div class="color-moment">
          <div class="color-swatch" id="moment-swatch"></div>
          <div class="color-info">
            <div class="hex" id="moment-hex">#------</div>
            <div id="moment-lab">L*=-- a*=-- b*=--</div>
            <div id="moment-tier">--</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card chart-tall">
        <h3>Seeds per L* Slice</h3>
        <canvas id="tier-chart"></canvas>
      </div>
      <div class="card chart-tall">
        <h3>Running Projection</h3>
        <canvas id="projection-chart"></canvas>
      </div>
    </div>

    <!-- Practical info -->
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card">
        <h3>System</h3>
        <div class="stat-row"><span class="label">Memory</span><span id="stat-memory">--</span></div>
        <div class="stat-row"><span class="label">Disk Usage</span><span id="stat-disk">--</span></div>
        <div class="stat-row"><span class="label">Last Checkpoint</span><span id="stat-checkpoint">--</span></div>
        <div class="stat-row"><span class="label">Valid Points</span><span id="stat-valid">--</span></div>
      </div>
      <div class="card">
        <h3>Run Log</h3>
        <div class="log-entries" id="run-log"></div>
      </div>
    </div>
  </div>
</div>

<script>
const POLL_MS = 5000;
let sliceData = [];
let lastStatus = null;

// ---- Data fetching ----
async function fetchJSON(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    return null;
  }
}

async function poll() {
  const status = await fetchJSON('/api/status');
  const conn = document.getElementById('connection-status');

  if (!status) {
    conn.textContent = 'Disconnected';
    conn.className = 'error';
    return;
  }
  conn.textContent = 'Live';
  conn.className = '';

  if (status.state === 'not_started') {
    document.getElementById('not-started').style.display = '';
    document.getElementById('dashboard').style.display = 'none';
    return;
  }

  document.getElementById('not-started').style.display = 'none';
  document.getElementById('dashboard').style.display = '';

  lastStatus = status;
  updateProgress(status);
  updateTierCounts(status);
  updateSystem(status);
  updateRunLog(status);

  // Fetch slice data less frequently
  if (!sliceData.length || Math.random() < 0.2) {
    const sd = await fetchJSON('/api/slices');
    if (sd && sd.length) {
      sliceData = sd;
      drawTierChart();
      drawProjection(status);
    }
  }

  // Fetch recent seeds for color of the moment
  const seeds = await fetchJSON('/api/recent-seeds');
  if (seeds && seeds.length) updateColorMoment(seeds[0]);

  drawColorStrip(status);
}

// ---- UI Updates ----
function updateProgress(s) {
  document.getElementById('progress-fill').style.width = s.progress_pct + '%';
  document.getElementById('stat-slice').textContent =
    'Slice ' + (s.current_slice + 1) + '/' + s.total_slices;
  document.getElementById('stat-L').textContent =
    'L* = ' + (s.current_L_value || 0).toFixed(2);
  document.getElementById('stat-elapsed').textContent =
    'Elapsed: ' + formatDuration(s.elapsed_seconds);
  document.getElementById('stat-eta').textContent =
    'ETA: ' + formatDuration(s.eta_seconds);
  document.getElementById('stat-rate').textContent =
    formatNum(s.rate_points_per_sec || 0) + ' pts/sec';
}

function updateTierCounts(s) {
  const seeds = s.seeds || {};
  document.getElementById('count-jnd').textContent = formatNum(seeds.JND || 0);
  document.getElementById('count-accept').textContent = formatNum(seeds.acceptability || 0);
  document.getElementById('count-obvious').textContent = formatNum(seeds.obvious || 0);
}

function updateSystem(s) {
  document.getElementById('stat-memory').textContent = (s.memory_mb || 0).toFixed(0) + ' MB';
  document.getElementById('stat-disk').textContent = (s.disk_usage_mb || 0).toFixed(0) + ' MB';
  document.getElementById('stat-valid').textContent = formatNum(s.total_valid_points || 0);

  if (s.last_checkpoint) {
    const ago = (Date.now() / 1000) - new Date(s.last_checkpoint).getTime() / 1000;
    document.getElementById('stat-checkpoint').textContent =
      ago < 120 ? Math.round(ago) + 's ago' : Math.round(ago / 60) + 'm ago';
  }
}

function updateRunLog(s) {
  const log = s.run_log || [];
  const el = document.getElementById('run-log');
  el.innerHTML = log.slice(-15).reverse().map(e =>
    '<div><span class="event">' + esc(e.event) + '</span> ' +
    '<span>' + esc(e.details || '') + '</span> ' +
    '<span style="float:right">' + timeAgo(e.time) + '</span></div>'
  ).join('');
}

function updateColorMoment(seed) {
  if (!seed) return;
  const hex = seed.hex_srgb || '#000000';
  document.getElementById('moment-swatch').style.backgroundColor = hex;
  document.getElementById('moment-hex').textContent = hex;
  document.getElementById('moment-lab').textContent =
    'L*=' + (seed.L||0).toFixed(1) + '  a*=' + (seed.a||0).toFixed(1) + '  b*=' + (seed.b||0).toFixed(1);
  document.getElementById('moment-tier').textContent = seed.tier_name || '';
}

// ---- Canvas Charts ----
function drawColorStrip(status) {
  const canvas = document.getElementById('strip-canvas');
  if (!canvas) return;
  const ctx = setupCanvas(canvas);
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const slices = status.completed_slices || [];
  if (!slices.length) return;

  const totalSlices = status.total_slices || 401;
  const bandW = w / totalSlices;

  for (const s of slices) {
    const x = (s.slice_id / totalSlices) * w;
    // Color from L* value — neutral gray at that lightness
    const gray = Math.round(s.L_value * 2.55);
    ctx.fillStyle = 'rgb(' + gray + ',' + gray + ',' + gray + ')';
    ctx.fillRect(x, 0, Math.max(bandW, 1), h);
  }
}

function drawTierChart() {
  const canvas = document.getElementById('tier-chart');
  if (!canvas || !sliceData.length) return;
  const ctx = setupCanvas(canvas);
  const w = canvas.width, h = canvas.height;
  const pad = { top: 10, right: 10, bottom: 30, left: 60 };

  ctx.clearRect(0, 0, w, h);

  // Group by tier
  const tiers = {};
  for (const row of sliceData) {
    if (!tiers[row.tier_name]) tiers[row.tier_name] = [];
    tiers[row.tier_name].push({ L: row.L_value, seeds: row.seeds_found });
  }

  // Find max seeds
  let maxSeeds = 0;
  for (const t of Object.values(tiers)) {
    for (const p of t) if (p.seeds > maxSeeds) maxSeeds = p.seeds;
  }
  if (maxSeeds === 0) return;

  const colors = { JND: '#58a6ff', acceptability: '#d29922', obvious: '#3fb950' };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  // Axes
  ctx.strokeStyle = '#30363d';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, h - pad.bottom);
  ctx.lineTo(w - pad.right, h - pad.bottom);
  ctx.stroke();

  // Y-axis label
  ctx.fillStyle = '#8b949e';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText(formatNum(maxSeeds), pad.left - 5, pad.top + 10);
  ctx.fillText('0', pad.left - 5, h - pad.bottom);

  // X-axis labels
  ctx.textAlign = 'center';
  ctx.fillText('0', pad.left, h - pad.bottom + 15);
  ctx.fillText('50', pad.left + plotW / 2, h - pad.bottom + 15);
  ctx.fillText('100', pad.left + plotW, h - pad.bottom + 15);

  // Draw lines
  for (const [name, points] of Object.entries(tiers)) {
    ctx.strokeStyle = colors[name] || '#999';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
      const x = pad.left + (points[i].L / 100) * plotW;
      const y = pad.top + plotH - (points[i].seeds / maxSeeds) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Legend
  let lx = pad.left + 10;
  ctx.font = '11px sans-serif';
  for (const [name, color] of Object.entries(colors)) {
    ctx.fillStyle = color;
    ctx.fillRect(lx, pad.top, 12, 3);
    ctx.fillStyle = '#8b949e';
    ctx.textAlign = 'left';
    ctx.fillText(name, lx + 16, pad.top + 5);
    lx += ctx.measureText(name).width + 35;
  }
}

function drawProjection(status) {
  const canvas = document.getElementById('projection-chart');
  if (!canvas || !sliceData.length) return;
  const ctx = setupCanvas(canvas);
  const w = canvas.width, h = canvas.height;
  const pad = { top: 10, right: 10, bottom: 30, left: 70 };

  ctx.clearRect(0, 0, w, h);

  const seeds = status.seeds || {};
  const progress = (status.current_slice + 1) / (status.total_slices || 1);
  if (progress < 0.02) return;

  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const tiers = [
    { name: 'JND', current: seeds.JND || 0, color: '#58a6ff' },
    { name: 'acceptability', current: seeds.acceptability || 0, color: '#d29922' },
    { name: 'obvious', current: seeds.obvious || 0, color: '#3fb950' },
  ];

  // Simple linear projection
  for (const t of tiers) t.projected = Math.round(t.current / progress);
  const maxProj = Math.max(...tiers.map(t => t.projected), 1);

  // Axes
  ctx.strokeStyle = '#30363d';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, h - pad.bottom);
  ctx.lineTo(w - pad.right, h - pad.bottom);
  ctx.stroke();

  // Draw projected bars
  const barW = plotW / (tiers.length * 2 + 1);
  for (let i = 0; i < tiers.length; i++) {
    const t = tiers[i];
    const x = pad.left + (i * 2 + 1) * barW;
    const barH = (t.projected / maxProj) * plotH;
    const filledH = (t.current / maxProj) * plotH;

    // Projected (dimmed)
    ctx.fillStyle = t.color + '33';
    ctx.fillRect(x, pad.top + plotH - barH, barW, barH);

    // Actual so far
    ctx.fillStyle = t.color;
    ctx.fillRect(x, pad.top + plotH - filledH, barW, filledH);

    // Label
    ctx.fillStyle = '#8b949e';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(t.name, x + barW / 2, h - pad.bottom + 15);
    ctx.fillStyle = t.color;
    ctx.fillText(formatBig(t.projected), x + barW / 2, pad.top + plotH - barH - 5);
  }
}

// ---- Canvas helpers ----
function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  // Return a context that draws at CSS pixel sizes
  canvas._cssW = rect.width;
  canvas._cssH = rect.height;
  return ctx;
}

// ---- Formatting ----
function formatNum(n) {
  return Number(n).toLocaleString('en-US');
}

function formatBig(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

function formatDuration(secs) {
  if (!secs || secs <= 0) return '--';
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return d + 'd ' + h + 'h ' + m + 'm';
  if (h > 0) return h + 'h ' + m + 'm';
  return m + 'm';
}

function timeAgo(ts) {
  if (!ts) return '';
  const secs = (Date.now() - new Date(ts).getTime()) / 1000;
  if (secs < 60) return Math.round(secs) + 's ago';
  if (secs < 3600) return Math.round(secs / 60) + 'm ago';
  return Math.round(secs / 3600) + 'h ago';
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ---- Main loop ----
poll();
setInterval(poll, POLL_MS);
</script>
</body>
</html>"""
