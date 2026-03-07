"""JND Visual Audit page.

Self-contained HTML/CSS/JS for perceptual validation of JND seed pairs.
Follows the same inline pattern as page.py — no external dependencies.
"""


def render_jnd_audit_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JND Visual Audit — Chromatic Census</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --accent: #58a6ff;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
    user-select: none;
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
  header a {
    color: var(--accent);
    text-decoration: none;
    font-size: 13px;
  }
  header a:hover { text-decoration: underline; }

  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 20px;
    margin-bottom: 20px;
    font-size: 15px;
  }
  .status-bar .seed-counter { color: var(--text); }
  .status-bar .neighbor-counter { color: var(--accent); font-weight: 600; }

  .slider-container {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 20px 10px;
    margin-bottom: 20px;
  }
  .slider-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .slider-row input[type="range"] {
    flex: 1;
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    outline: none;
    cursor: pointer;
  }
  .slider-row input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg);
  }
  .slider-row input[type="range"]::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg);
  }
  .slider-row .slider-value {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 14px;
    color: var(--accent);
    min-width: 110px;
    text-align: right;
  }
  .slider-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
  }

  /* Three-panel swatch layout */
  .swatch-area {
    position: relative;
    margin-bottom: 16px;
    cursor: pointer;
  }

  .swatch-trio {
    display: flex;
    align-items: flex-end;
    width: 100%;
    gap: 0;
  }
  .swatch-neighbor {
    flex: 1;
    height: 360px;
    position: relative;
    transition: background-color 0.15s ease;
  }
  .swatch-ref {
    flex: 1;
    height: 440px;
    position: relative;
    transition: background-color 0.15s ease;
  }
  .swatch-solo {
    width: 100%;
    height: 440px;
    border-radius: 8px;
    transition: background-color 0.15s ease;
  }

  /* Round outer corners only */
  .swatch-trio .swatch-neighbor:first-child {
    border-radius: 8px 0 0 0;
  }
  .swatch-trio .swatch-neighbor:last-child {
    border-radius: 0 8px 0 0;
  }
  .swatch-trio .swatch-ref {
    border-radius: 8px 8px 0 0;
  }

  /* ΔE overlay on neighbor swatches */
  .de-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    background: rgba(0, 0, 0, 0.45);
    padding: 6px 14px;
    border-radius: 6px;
    pointer-events: none;
  }

  /* Labels row below swatches */
  .labels-row {
    display: flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0 0 8px 8px;
    overflow: hidden;
  }
  .label-col {
    flex: 1;
    padding: 10px 12px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.5;
    text-align: center;
  }
  .label-col-ref {
    flex: 1;
  }
  .label-col + .label-col {
    border-left: 1px solid var(--border);
  }
  .label-col .hex {
    font-weight: 600;
    color: var(--accent);
  }
  .label-col .lab {
    color: var(--text-dim);
  }

  .no-neighbors-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 15px;
    padding: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0 0 8px 8px;
  }

  .gap-nav {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }
  .gap-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--accent);
    font-size: 13px;
    padding: 6px 14px;
    cursor: pointer;
    font-family: inherit;
    transition: border-color 0.15s;
  }
  .gap-btn:hover {
    border-color: var(--accent);
  }
  .gap-info {
    color: var(--text-dim);
    font-size: 12px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  }

  .hint {
    text-align: center;
    color: var(--text-dim);
    font-size: 13px;
    margin-top: 16px;
  }

  .loading {
    text-align: center;
    padding: 100px 20px;
    color: var(--text-dim);
    font-size: 16px;
  }
</style>
</head>
<body>

<header>
  <h1>JND Visual Audit</h1>
  <a href="/">&larr; Back to Census</a>
</header>

<div id="app">
  <div class="loading" id="loading">Loading sRGB JND seeds...</div>
</div>

<script>
(function() {
  const app = document.getElementById('app');
  const loadingEl = document.getElementById('loading');

  const state = {
    offset: 0,
    total: 0,
    seed: null,
    prev: null,   // previous seed in chain walk
    next: null,   // next seed in chain walk
    loading: true,
    gaps: [],     // sorted by ΔE descending
    gapRank: 0,   // current position in gaps list
    gapStats: null,
  };

  function render() {
    if (state.loading) return;

    if (!state.seed) {
      app.innerHTML = '<div class="loading">No sRGB JND seeds found.</div>';
      return;
    }

    var left = state.prev;
    var right = state.next;
    var html = '';

    // Status bar
    html += '<div class="status-bar">';
    html += '<span class="seed-counter">Seed ' + (state.offset + 1) + ' of ' + state.total.toLocaleString() + '</span>';
    html += '<span class="neighbor-counter">L*=' + state.seed.L.toFixed(1) + '</span>';
    html += '</div>';

    // Slider
    html += '<div class="slider-container">';
    html += '<div class="slider-label"><span>Perceptual chain walk</span><span>' + (state.offset + 1).toLocaleString() + ' / ' + state.total.toLocaleString() + '</span></div>';
    html += '<div class="slider-row">';
    html += '<input type="range" id="seed-slider" min="1" max="' + state.total + '" value="' + (state.offset + 1) + '">';
    html += '<span class="slider-value">L*=' + state.seed.L.toFixed(1) + '</span>';
    html += '</div>';
    html += '</div>';

    // Swatch area
    html += '<div class="swatch-area" id="swatch-area">';
    html += '<div class="swatch-trio">';

    if (left) {
      html += '<div class="swatch-neighbor" style="background-color: ' + left.hex + '">';
      html += '<div class="de-overlay">&Delta;E ' + left.delta_e.toFixed(2) + '</div>';
      html += '</div>';
    }

    html += '<div class="swatch-ref" style="background-color: ' + state.seed.hex + '"></div>';

    if (right) {
      html += '<div class="swatch-neighbor" style="background-color: ' + right.hex + '">';
      html += '<div class="de-overlay">&Delta;E ' + right.delta_e.toFixed(2) + '</div>';
      html += '</div>';
    }

    html += '</div>';

    // Labels
    html += '<div class="labels-row">';
    if (left) {
      html += '<div class="label-col">';
      html += '<span class="lab">L*=' + left.L.toFixed(2) + ', a=' + left.a.toFixed(2) + ', b=' + left.b.toFixed(2) + '</span><br>';
      html += '<span class="hex">' + left.hex + '</span>';
      html += '</div>';
    }
    html += '<div class="label-col label-col-ref">';
    html += '<span class="lab">L*=' + state.seed.L.toFixed(2) + ', a=' + state.seed.a.toFixed(2) + ', b=' + state.seed.b.toFixed(2) + '</span><br>';
    html += '<span class="hex">' + state.seed.hex + '</span>';
    html += '</div>';
    if (right) {
      html += '<div class="label-col">';
      html += '<span class="lab">L*=' + right.L.toFixed(2) + ', a=' + right.a.toFixed(2) + ', b=' + right.b.toFixed(2) + '</span><br>';
      html += '<span class="hex">' + right.hex + '</span>';
      html += '</div>';
    }
    html += '</div>';

    html += '</div>';

    // Gap navigation
    if (state.gaps.length > 0) {
      var g = state.gaps[state.gapRank];
      html += '<div class="gap-nav">';
      html += '<button class="gap-btn" id="gap-prev">&larr; prev gap</button>';
      html += '<button class="gap-btn" id="gap-jump">Jump to #' + (state.gapRank + 1) + ' gap (&Delta;E ' + g.delta_e.toFixed(2) + ')</button>';
      html += '<button class="gap-btn" id="gap-next">next gap &rarr;</button>';
      if (state.gapStats) {
        html += '<span class="gap-info">max=' + state.gapStats.max.toFixed(2) + ' med=' + state.gapStats.median.toFixed(2) + '</span>';
      }
      html += '</div>';
    }

    // Hint
    html += '<div class="hint"><b>Space</b> / <b>Click</b> / <b>&rarr;</b> = next &nbsp;&bull;&nbsp; <b>&larr;</b> = prev &nbsp;&bull;&nbsp; <b>Slider</b> = jump</div>';

    app.innerHTML = html;

    // Re-bind click handler
    var swatchArea = document.getElementById('swatch-area');
    if (swatchArea) {
      swatchArea.addEventListener('click', advance);
    }

    // Bind gap buttons
    var gapPrev = document.getElementById('gap-prev');
    var gapJump = document.getElementById('gap-jump');
    var gapNext = document.getElementById('gap-next');
    if (gapPrev) gapPrev.addEventListener('click', function(e) {
      e.stopPropagation();
      if (state.gapRank > 0) { state.gapRank--; render(); }
    });
    if (gapNext) gapNext.addEventListener('click', function(e) {
      e.stopPropagation();
      if (state.gapRank < state.gaps.length - 1) { state.gapRank++; render(); }
    });
    if (gapJump) gapJump.addEventListener('click', function(e) {
      e.stopPropagation();
      var g = state.gaps[state.gapRank];
      jumpToSeed(g.offset);
    });

    // Bind slider
    var slider = document.getElementById('seed-slider');
    if (slider) {
      var sliderTimer = null;
      slider.addEventListener('input', function() {
        var valSpan = this.parentElement.querySelector('.slider-value');
        if (valSpan) valSpan.textContent = 'L*=' + state.seed.L.toFixed(1);
        clearTimeout(sliderTimer);
        sliderTimer = setTimeout(function() {
          var newOffset = parseInt(slider.value) - 1;
          if (newOffset !== state.offset) {
            jumpToSeed(newOffset);
          }
        }, 150);
      });
    }
  }

  async function loadSeed(offset) {
    var res = await fetch('/api/jnd-audit/seed?offset=' + offset);
    var data = await res.json();
    state.offset = data.offset;
    state.total = data.total;
    state.seed = data.seed;
    state.prev = data.prev;
    state.next = data.next;
  }

  async function jumpToSeed(offset) {
    offset = Math.max(0, Math.min(offset, state.total - 1));
    await loadSeed(offset);
    render();
  }

  async function advance() {
    if (state.offset + 1 < state.total) {
      await loadSeed(state.offset + 1);
      render();
    }
  }

  // Keyboard handler
  document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' || e.code === 'ArrowRight') {
      e.preventDefault();
      advance();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      if (state.offset > 0) jumpToSeed(state.offset - 1);
    }
  });

  async function loadGaps() {
    var res = await fetch('/api/jnd-audit/gaps?count=100');
    var data = await res.json();
    state.gaps = data.gaps || [];
    state.gapStats = data.stats || null;
  }

  // Initial load
  (async function() {
    await loadSeed(0);
    state.loading = false;
    loadingEl.style.display = 'none';
    render();
    // Load gaps in background (non-blocking)
    loadGaps().then(function() { render(); });
  })();

})();
</script>
</body>
</html>"""
