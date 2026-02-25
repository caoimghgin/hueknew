"""JND Neighborhood page.

Orbital neighborhood view — shows ALL seeds within a ΔE radius of the
reference, projected as a radial layout. "Think in three dimensions."
"""


def render_jnd_neighborhood_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JND Neighborhood — Chromatic Census</title>
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

  .controls {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 20px 14px;
    margin-bottom: 20px;
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
    width: 18px; height: 18px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg);
  }
  .slider-row input[type="range"]::-moz-range-thumb {
    width: 18px; height: 18px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid var(--bg);
  }
  .slider-row .slider-value {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 14px;
    color: var(--accent);
    min-width: 80px;
    text-align: right;
  }

  .threshold-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .threshold-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-right: auto;
  }
  .threshold-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text-dim);
    font-size: 12px;
    padding: 4px 12px;
    cursor: pointer;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    transition: all 0.15s;
  }
  .threshold-btn:hover { border-color: var(--accent); color: var(--text); }
  .threshold-btn.active {
    background: var(--accent);
    color: #000;
    border-color: var(--accent);
    font-weight: 600;
  }

  /* Orbital view */
  .orbital-container {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1;
    max-width: 860px;
    margin: 0 auto 20px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }

  .ring-guide {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    border: 1px dashed var(--border);
    border-radius: 50%;
    pointer-events: none;
  }
  .ring-label {
    position: absolute;
    top: 2px; left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--text-dim);
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    background: var(--bg);
    padding: 0 4px;
    opacity: 0.6;
  }

  .ref-swatch {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 140px; height: 140px;
    border-radius: 50%;
    border: 3px solid #fff;
    box-shadow: 0 0 0 6px rgba(255,255,255,0.1);
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ref-label {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #fff;
    background: rgba(0,0,0,0.5);
    padding: 3px 10px;
    border-radius: 6px;
    pointer-events: none;
  }

  .orbital-swatch {
    position: absolute;
    border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.15);
    cursor: pointer;
    transition: transform 0.15s, border-color 0.15s, z-index 0s;
    z-index: 5;
  }
  .orbital-swatch:hover {
    transform: scale(1.35);
    border-color: var(--accent);
    z-index: 20;
  }
  .orbital-swatch.highlighted {
    border-color: var(--accent);
    z-index: 20;
    transform: scale(1.25);
  }
  .swatch-de-label {
    position: absolute;
    bottom: -18px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 10px;
    color: #fff;
    background: rgba(0,0,0,0.7);
    padding: 1px 5px;
    border-radius: 8px;
    white-space: nowrap;
    pointer-events: none;
  }

  /* Neighbor list */
  .neighbor-list {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    max-height: 260px;
    overflow-y: auto;
    margin-bottom: 16px;
  }
  .neighbor-list-header {
    display: flex;
    justify-content: space-between;
    padding: 10px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--surface);
    z-index: 2;
  }
  .neighbor-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.1s;
  }
  .neighbor-row:hover, .neighbor-row.highlighted {
    background: rgba(88, 166, 255, 0.08);
  }
  .neighbor-row:last-child { border-bottom: none; }
  .neighbor-mini-swatch {
    width: 24px; height: 24px;
    border-radius: 4px;
    flex-shrink: 0;
    border: 1px solid rgba(255,255,255,0.1);
  }
  .neighbor-hex {
    color: var(--accent);
    font-weight: 600;
    min-width: 72px;
  }
  .neighbor-de { min-width: 56px; }
  .de-bar {
    display: inline-block;
    height: 3px;
    background: var(--accent);
    border-radius: 1.5px;
    vertical-align: middle;
    margin-left: 4px;
  }
  .neighbor-lab { color: var(--text-dim); }

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
  <h1>JND Neighborhood</h1>
  <a href="/">&larr; Back to Census</a>
</header>

<div id="app">
  <div class="loading" id="loading">Loading sRGB JND seeds...</div>
</div>

<script>
(function() {
  var app = document.getElementById('app');
  var loadingEl = document.getElementById('loading');

  var GOLDEN_ANGLE = 137.508 * Math.PI / 180;
  var THRESHOLDS = [1.0, 1.5, 2.0, 3.0];

  var state = {
    offset: 0,
    total: 0,
    seed: null,
    neighbors: [],
    threshold: 2.0,
    loading: true,
    highlightIdx: -1,
  };

  function layoutNeighbors(neighbors, containerSize, maxDE) {
    var centerX = containerSize / 2;
    var centerY = containerSize / 2;
    var refRadius = 70;
    var padding = 30;
    var usableRadius = (containerSize / 2) - padding;

    var swatchSize;
    var n = neighbors.length;
    if (n <= 8) swatchSize = 72;
    else if (n <= 16) swatchSize = 56;
    else if (n <= 24) swatchSize = 44;
    else swatchSize = 36;

    var positions = [];
    for (var i = 0; i < n; i++) {
      var nb = neighbors[i];
      var minDist = refRadius + swatchSize / 2 + 10;
      var maxDist = usableRadius - swatchSize / 2;
      var t = nb.delta_e / maxDE;
      var dist = minDist + t * (maxDist - minDist);

      var angle;
      if (n <= 6) {
        angle = (i / n) * 2 * Math.PI - Math.PI / 2;
      } else {
        angle = i * GOLDEN_ANGLE;
      }

      var x = centerX + dist * Math.cos(angle) - swatchSize / 2;
      var y = centerY + dist * Math.sin(angle) - swatchSize / 2;

      positions.push({ x: x, y: y, size: swatchSize, neighbor: nb, idx: i });
    }
    return positions;
  }

  function render() {
    if (state.loading) return;
    if (!state.seed) {
      app.innerHTML = '<div class="loading">No sRGB JND seeds found.</div>';
      return;
    }

    var nn = state.neighbors;
    var html = '';

    // Status bar
    html += '<div class="status-bar">';
    html += '<span class="seed-counter">Seed ' + (state.offset + 1) + ' of ' + state.total.toLocaleString() + '</span>';
    html += '<span class="neighbor-counter">' + nn.length + ' neighbor' + (nn.length !== 1 ? 's' : '') + ' within &Delta;E &le; ' + state.threshold.toFixed(1) + '</span>';
    html += '</div>';

    // Controls
    html += '<div class="controls">';
    html += '<div class="slider-label"><span>Perceptual chain walk</span><span>' + (state.offset + 1).toLocaleString() + ' / ' + state.total.toLocaleString() + '</span></div>';
    html += '<div class="slider-row">';
    html += '<input type="range" id="seed-slider" min="1" max="' + state.total + '" value="' + (state.offset + 1) + '">';
    html += '<span class="slider-value">L*=' + state.seed.L.toFixed(1) + '</span>';
    html += '</div>';
    html += '<div class="threshold-row">';
    html += '<span class="threshold-label">Neighborhood radius</span>';
    for (var t = 0; t < THRESHOLDS.length; t++) {
      var tv = THRESHOLDS[t];
      var active = tv === state.threshold ? ' active' : '';
      html += '<button class="threshold-btn' + active + '" data-threshold="' + tv + '">' + tv.toFixed(1) + '</button>';
    }
    html += '</div>';
    html += '</div>';

    // Orbital view
    var containerSize = 860;
    html += '<div class="orbital-container" id="orbital" style="max-width:' + containerSize + 'px">';

    // Ring guides
    var rings = [
      { pct: 38, label: '&Delta;E ' + (state.threshold * 0.375).toFixed(2) },
      { pct: 62, label: '&Delta;E ' + (state.threshold * 0.625).toFixed(2) },
      { pct: 90, label: '&Delta;E ' + state.threshold.toFixed(1) },
    ];
    for (var r = 0; r < rings.length; r++) {
      html += '<div class="ring-guide" style="width:' + rings[r].pct + '%;height:' + rings[r].pct + '%">';
      html += '<span class="ring-label">' + rings[r].label + '</span>';
      html += '</div>';
    }

    // Reference swatch
    html += '<div class="ref-swatch" style="background-color:' + state.seed.hex + '">';
    html += '<span class="ref-label">' + state.seed.hex + '</span>';
    html += '</div>';

    // Neighbor orbital swatches
    var positions = layoutNeighbors(nn, containerSize, state.threshold);
    for (var p = 0; p < positions.length; p++) {
      var pos = positions[p];
      var nb = pos.neighbor;
      var hl = state.highlightIdx === pos.idx ? ' highlighted' : '';
      html += '<div class="orbital-swatch' + hl + '" data-idx="' + pos.idx + '" style="';
      html += 'left:' + pos.x.toFixed(1) + 'px;top:' + pos.y.toFixed(1) + 'px;';
      html += 'width:' + pos.size + 'px;height:' + pos.size + 'px;';
      html += 'background-color:' + nb.hex + '">';
      if (nn.length <= 20) {
        html += '<span class="swatch-de-label">' + nb.delta_e.toFixed(2) + '</span>';
      }
      html += '</div>';
    }

    html += '</div>';

    // Neighbor list
    if (nn.length > 0) {
      html += '<div class="neighbor-list" id="neighbor-list">';
      html += '<div class="neighbor-list-header"><span>Neighbors (' + nn.length + ')</span><span>sorted by &Delta;E &uarr;</span></div>';
      for (var i = 0; i < nn.length; i++) {
        var nb = nn[i];
        var hl = state.highlightIdx === i ? ' highlighted' : '';
        var barW = Math.round((nb.delta_e / state.threshold) * 60);
        html += '<div class="neighbor-row' + hl + '" data-idx="' + i + '">';
        html += '<div class="neighbor-mini-swatch" style="background-color:' + nb.hex + '"></div>';
        html += '<span class="neighbor-hex">' + nb.hex + '</span>';
        html += '<span class="neighbor-de">&Delta;E ' + nb.delta_e.toFixed(2) + '<span class="de-bar" style="width:' + barW + 'px"></span></span>';
        html += '<span class="neighbor-lab">L*=' + nb.L.toFixed(1) + ' a=' + nb.a.toFixed(1) + ' b=' + nb.b.toFixed(1) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    // Hint
    html += '<div class="hint"><b>&rarr;</b> = next &nbsp;&bull;&nbsp; <b>&larr;</b> = prev &nbsp;&bull;&nbsp; <b>Click orbit</b> = navigate to neighbor &nbsp;&bull;&nbsp; <b>Slider</b> = jump</div>';

    app.innerHTML = html;
    bindEvents();
  }

  function bindEvents() {
    // Slider
    var slider = document.getElementById('seed-slider');
    if (slider) {
      var sliderTimer = null;
      slider.addEventListener('input', function() {
        clearTimeout(sliderTimer);
        sliderTimer = setTimeout(function() {
          var newOffset = parseInt(slider.value) - 1;
          if (newOffset !== state.offset) {
            jumpToSeed(newOffset);
          }
        }, 150);
      });
    }

    // Threshold buttons
    var buttons = document.querySelectorAll('.threshold-btn');
    for (var b = 0; b < buttons.length; b++) {
      buttons[b].addEventListener('click', function(e) {
        var newThreshold = parseFloat(this.getAttribute('data-threshold'));
        if (newThreshold !== state.threshold) {
          state.threshold = newThreshold;
          loadNeighbors(state.offset, newThreshold).then(render);
        }
      });
    }

    // Orbital swatch clicks → navigate to that seed
    var orbitals = document.querySelectorAll('.orbital-swatch');
    for (var o = 0; o < orbitals.length; o++) {
      (function(el) {
        el.addEventListener('click', function() {
          var idx = parseInt(this.getAttribute('data-idx'));
          var nb = state.neighbors[idx];
          // Find this seed's offset in the chain walk
          navigateToSeedId(nb.id);
        });
        el.addEventListener('mouseenter', function() {
          var idx = parseInt(this.getAttribute('data-idx'));
          highlightNeighbor(idx);
        });
        el.addEventListener('mouseleave', function() {
          highlightNeighbor(-1);
        });
      })(orbitals[o]);
    }

    // Neighbor list row hover/click
    var rows = document.querySelectorAll('.neighbor-row');
    for (var r = 0; r < rows.length; r++) {
      (function(el) {
        el.addEventListener('click', function() {
          var idx = parseInt(this.getAttribute('data-idx'));
          var nb = state.neighbors[idx];
          navigateToSeedId(nb.id);
        });
        el.addEventListener('mouseenter', function() {
          var idx = parseInt(this.getAttribute('data-idx'));
          highlightNeighbor(idx);
        });
        el.addEventListener('mouseleave', function() {
          highlightNeighbor(-1);
        });
      })(rows[r]);
    }
  }

  function highlightNeighbor(idx) {
    state.highlightIdx = idx;
    // Update highlights without full re-render
    var orbitals = document.querySelectorAll('.orbital-swatch');
    for (var i = 0; i < orbitals.length; i++) {
      var oidx = parseInt(orbitals[i].getAttribute('data-idx'));
      orbitals[i].classList.toggle('highlighted', oidx === idx);
    }
    var rows = document.querySelectorAll('.neighbor-row');
    for (var i = 0; i < rows.length; i++) {
      var ridx = parseInt(rows[i].getAttribute('data-idx'));
      rows[i].classList.toggle('highlighted', ridx === idx);
      if (ridx === idx && idx >= 0) {
        rows[i].scrollIntoView({ block: 'nearest' });
      }
    }
  }

  async function loadSeed(offset) {
    var res = await fetch('/api/jnd-audit/seed?offset=' + offset);
    var data = await res.json();
    state.offset = data.offset;
    state.total = data.total;
    state.seed = data.seed;
  }

  async function loadNeighbors(offset, threshold) {
    var res = await fetch('/api/jnd-audit/neighbors?offset=' + offset + '&threshold=' + threshold);
    var data = await res.json();
    state.neighbors = data.neighbors || [];
    state.highlightIdx = -1;
  }

  async function jumpToSeed(offset) {
    offset = Math.max(0, Math.min(offset, state.total - 1));
    await Promise.all([
      loadSeed(offset),
      loadNeighbors(offset, state.threshold),
    ]);
    render();
  }

  async function navigateToSeedId(seedId) {
    // Load neighbors by seed_id instead of offset
    var res = await fetch('/api/jnd-audit/neighbors?seed_id=' + seedId + '&threshold=' + state.threshold);
    var data = await res.json();
    state.neighbors = data.neighbors || [];
    state.highlightIdx = -1;
    // Also load the seed data — use the reference from neighbors response
    if (data.reference) {
      state.seed = data.reference;
      // Find offset in chain walk (approximate — scan is expensive, just update display)
      state.seed.hex = data.reference.hex;
    }
    render();
  }

  // Keyboard handler
  document.addEventListener('keydown', function(e) {
    if (e.code === 'ArrowRight') {
      e.preventDefault();
      if (state.offset + 1 < state.total) jumpToSeed(state.offset + 1);
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      if (state.offset > 0) jumpToSeed(state.offset - 1);
    }
  });

  // Initial load
  (async function() {
    await Promise.all([
      loadSeed(0),
      loadNeighbors(0, state.threshold),
    ]);
    state.loading = false;
    loadingEl.style.display = 'none';
    render();
  })();

})();
</script>
</body>
</html>"""
