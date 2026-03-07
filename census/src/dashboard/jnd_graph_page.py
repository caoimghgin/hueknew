"""JND Graph page.

Force-directed neighborhood graph — shows the true 3D packing topology
with inter-neighbor edges. "Think in three dimensions."
"""


def render_jnd_graph_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JND Graph — Chromatic Census</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
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
    max-width: 1100px;
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

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 12px;
  }

  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 13px;
  }
  .status-bar .lstar { color: var(--accent); font-weight: 600; }

  .slider-row {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
  }
  .slider-row label { color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }
  .slider-row input[type=range] { flex: 1; accent-color: var(--accent); }
  .slider-row .slider-info { text-align: right; min-width: 140px; white-space: nowrap; }
  .slider-row .slider-info .lstar { color: var(--accent); }

  .controls-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    font-size: 12px;
  }
  .controls-row .label {
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    margin-right: 4px;
  }
  .ctrl-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 4px 12px;
    border-radius: 14px;
    cursor: pointer;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
    transition: all 0.15s;
  }
  .ctrl-btn:hover { border-color: var(--accent); color: var(--text); }
  .ctrl-btn.active { background: var(--accent); color: #0d1117; border-color: var(--accent); font-weight: 600; }
  .ctrl-sep { width: 1px; height: 20px; background: var(--border); margin: 0 4px; }

  .graph-wrap {
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 12px;
    aspect-ratio: 16 / 10;
  }
  .graph-wrap svg { display: block; width: 100%; height: 100%; }

  .tooltip {
    position: absolute;
    pointer-events: none;
    background: rgba(22, 27, 34, 0.95);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11px;
    color: var(--text);
    line-height: 1.6;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 100;
    white-space: nowrap;
  }
  .tooltip.visible { opacity: 1; }

  .stats-row {
    display: flex;
    gap: 24px;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
    color: var(--text-dim);
    justify-content: center;
  }
  .stats-row span { color: var(--text); }

  .hint {
    text-align: center;
    font-size: 12px;
    color: var(--text-dim);
    margin-top: 8px;
  }

  .loading {
    text-align: center;
    padding: 80px 20px;
    color: var(--text-dim);
    font-size: 16px;
  }
</style>
</head>
<body>
<header>
  <h1>JND Graph</h1>
  <a href="/">&larr; Back to Census</a>
</header>
<div id="app">
  <div class="loading">Loading sRGB JND seeds&hellip;</div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
(function() {
  var app = document.getElementById('app');
  var tip = document.getElementById('tooltip');

  var state = {
    offset: 0,
    total: 0,
    focus: null,
    nodes: [],
    edges: [],
    stats: {},
    threshold: 1.5,
    depth: 2,
    loading: true,
  };

  // --- Data fetching ---
  async function loadGraph(offset, threshold, depth) {
    var url = '/api/jnd-graph?offset=' + offset +
              '&threshold=' + threshold +
              '&depth=' + depth;
    var res = await fetch(url);
    var data = await res.json();
    state.offset = data.offset;
    state.total = data.total;
    state.focus = data.focus;
    state.nodes = data.nodes;
    state.edges = data.edges;
    state.stats = data.stats;
    state.loading = false;
  }

  async function navigateTo(lstarOffset) {
    state.loading = true;
    render();
    await loadGraph(lstarOffset, state.threshold, state.depth);
    render();
    buildGraph();
  }

  // --- Render UI chrome (status, slider, controls) ---
  function render() {
    if (state.loading && state.total === 0) {
      app.innerHTML = '<div class="loading">Loading sRGB JND seeds&hellip;</div>';
      return;
    }
    if (state.loading) {
      // keep existing UI, just show loading overlay
      return;
    }
    if (!state.focus) {
      app.innerHTML = '<div class="loading">No seeds found.</div>';
      return;
    }

    var f = state.focus;
    var s = state.stats;
    var html = '';

    // Status bar
    html += '<div class="card status-bar">';
    html += '<span>Seed ' + (state.offset + 1) + ' of ' + state.total.toLocaleString() + '</span>';
    html += '<span class="lstar">L*=' + f.L.toFixed(1) + '</span>';
    html += '</div>';

    // Slider
    html += '<div class="card slider-row">';
    html += '<label>L*-sorted</label>';
    html += '<input type="range" id="seed-slider" min="1" max="' + state.total + '" value="' + (state.offset + 1) + '">';
    html += '<div class="slider-info">' + (state.offset + 1) + ' / ' + state.total.toLocaleString();
    html += ' <span class="lstar">L*=' + f.L.toFixed(1) + '</span></div>';
    html += '</div>';

    // Controls
    html += '<div class="card controls-row">';
    html += '<span class="label">&Delta;E radius</span>';
    var thresholds = [1.0, 1.5, 2.0];
    for (var t = 0; t < thresholds.length; t++) {
      var cls = thresholds[t] === state.threshold ? 'ctrl-btn active' : 'ctrl-btn';
      html += '<button class="' + cls + ' threshold-btn" data-t="' + thresholds[t] + '">' + thresholds[t].toFixed(1) + '</button>';
    }
    html += '<div class="ctrl-sep"></div>';
    html += '<span class="label">Depth</span>';
    for (var d = 1; d <= 2; d++) {
      var cls2 = d === state.depth ? 'ctrl-btn active' : 'ctrl-btn';
      html += '<button class="' + cls2 + ' depth-btn" data-d="' + d + '">' + d + '</button>';
    }
    html += '</div>';

    // Graph container
    html += '<div class="graph-wrap" id="graph-wrap"></div>';

    // Stats
    html += '<div class="stats-row">';
    html += 'depth-1: <span>' + s.depth_1_count + '</span>';
    html += '&nbsp;&nbsp;depth-2: <span>' + s.depth_2_count + '</span>';
    html += '&nbsp;&nbsp;nodes: <span>' + s.total_nodes + '</span>';
    html += '&nbsp;&nbsp;edges: <span>' + s.total_edges + '</span>';
    html += '</div>';

    // Hint
    html += '<div class="hint">Click a neighbor to re-center &middot; Arrow keys to step &middot; Slider to jump</div>';

    app.innerHTML = html;
    bindControls();
  }

  function bindControls() {
    // Slider
    var slider = document.getElementById('seed-slider');
    if (slider) {
      var timer = null;
      slider.addEventListener('input', function() {
        clearTimeout(timer);
        timer = setTimeout(function() {
          var off = parseInt(slider.value) - 1;
          if (off !== state.offset) navigateTo(off);
        }, 150);
      });
    }
    // Threshold buttons
    var tBtns = document.querySelectorAll('.threshold-btn');
    for (var i = 0; i < tBtns.length; i++) {
      tBtns[i].addEventListener('click', function() {
        var nt = parseFloat(this.getAttribute('data-t'));
        if (nt !== state.threshold) {
          state.threshold = nt;
          navigateTo(state.offset);
        }
      });
    }
    // Depth buttons
    var dBtns = document.querySelectorAll('.depth-btn');
    for (var i = 0; i < dBtns.length; i++) {
      dBtns[i].addEventListener('click', function() {
        var nd = parseInt(this.getAttribute('data-d'));
        if (nd !== state.depth) {
          state.depth = nd;
          navigateTo(state.offset);
        }
      });
    }
  }

  // --- D3 Force Graph ---
  function buildGraph() {
    var wrap = document.getElementById('graph-wrap');
    if (!wrap || !state.nodes.length) return;

    var rect = wrap.getBoundingClientRect();
    var W = rect.width;
    var H = rect.height;
    var padX = 90;
    var padY = 50;

    // Clear any previous SVG
    wrap.innerHTML = '';

    var svg = d3.select(wrap).append('svg')
      .attr('width', W).attr('height', H);

    // Axis labels
    svg.append('text').attr('class', 'axis-label')
      .attr('x', padX).attr('y', 22)
      .attr('fill', '#8b949e').attr('font-size', 10).attr('opacity', 0.5)
      .attr('font-family', 'SF Mono, Cascadia Code, Fira Code, monospace')
      .attr('letter-spacing', 1).text('CLOSER \\u0394E');
    svg.append('text').attr('class', 'axis-label')
      .attr('x', W - padX).attr('y', 22).attr('text-anchor', 'end')
      .attr('fill', '#8b949e').attr('font-size', 10).attr('opacity', 0.5)
      .attr('font-family', 'SF Mono, Cascadia Code, Fira Code, monospace')
      .attr('letter-spacing', 1).text('FARTHER \\u0394E');
    svg.append('text')
      .attr('x', 16).attr('y', padY + 10)
      .attr('fill', '#8b949e').attr('font-size', 10).attr('opacity', 0.5)
      .attr('font-family', 'SF Mono, Cascadia Code, Fira Code, monospace')
      .attr('letter-spacing', 1).text('DARKER');
    svg.append('text')
      .attr('x', 16).attr('y', H - padY + 5)
      .attr('fill', '#8b949e').attr('font-size', 10).attr('opacity', 0.5)
      .attr('font-family', 'SF Mono, Cascadia Code, Fira Code, monospace')
      .attr('letter-spacing', 1).text('LIGHTER');

    // Compute layout targets
    var maxDE = 0;
    for (var i = 0; i < state.nodes.length; i++) {
      if (state.nodes[i].de_focus > maxDE) maxDE = state.nodes[i].de_focus;
    }
    if (maxDE < 0.01) maxDE = state.threshold;

    // Compute L* range for y-axis
    var minL = 100, maxL = 0;
    for (var i = 0; i < state.nodes.length; i++) {
      if (state.nodes[i].L < minL) minL = state.nodes[i].L;
      if (state.nodes[i].L > maxL) maxL = state.nodes[i].L;
    }
    var Lpad = Math.max((maxL - minL) * 0.1, 2);
    minL = Math.max(0, minL - Lpad);
    maxL = Math.min(100, maxL + Lpad);
    if (maxL - minL < 5) { minL = Math.max(0, minL - 3); maxL = Math.min(100, maxL + 3); }

    var w = W - padX * 2;
    var h = H - padY * 2;

    var radiusByDepth = [40, 24, 14];

    // Prepare D3 nodes
    var simNodes = state.nodes.map(function(n, i) {
      var xT = padX + (n.de_focus / maxDE) * w * 0.85;
      var yT = padY + ((n.L - minL) / (maxL - minL)) * h;
      return {
        index: i,
        data: n,
        x: xT + (Math.random() - 0.5) * 10,
        y: yT + (Math.random() - 0.5) * 10,
        xTarget: xT,
        yTarget: yT,
        r: radiusByDepth[n.depth] || 14,
      };
    });

    // Pin focus node to left
    if (simNodes.length > 0) {
      simNodes[0].fx = padX + 10;
      simNodes[0].fy = padY + ((state.focus.L - minL) / (maxL - minL)) * h;
    }

    // Prepare D3 edges
    var simEdges = state.edges.map(function(e) {
      return { source: e.source, target: e.target, de: e.de };
    });

    // Edge group (below nodes)
    var edgeG = svg.append('g');
    var edgeEls = edgeG.selectAll('line')
      .data(simEdges).join('line')
      .attr('stroke', function(d) {
        var a = 0.08 + (1.0 - d.de / state.threshold) * 0.15;
        return 'rgba(255,255,255,' + Math.max(0.05, a).toFixed(3) + ')';
      })
      .attr('stroke-width', function(d) {
        return 0.8 + (1.0 - d.de / state.threshold) * 1.2;
      })
      .attr('stroke-linecap', 'round');

    // Node group
    var nodeG = svg.append('g');
    var nodeEls = nodeG.selectAll('circle')
      .data(simNodes).join('circle')
      .attr('r', function(d) { return d.r; })
      .attr('fill', function(d) { return d.data.hex; })
      .attr('stroke', function(d) {
        return d.data.depth === 0 ? '#ffffff' :
               d.data.depth === 1 ? 'rgba(255,255,255,0.25)' : 'none';
      })
      .attr('stroke-width', function(d) { return d.data.depth === 0 ? 3 : 1.5; })
      .attr('opacity', function(d) { return d.data.depth <= 1 ? 1.0 : 0.55; })
      .attr('cursor', function(d) { return d.data.depth > 0 ? 'pointer' : 'default'; })
      .on('click', function(event, d) {
        if (d.data.depth > 0) {
          navigateTo(d.data.lstar_offset);
        }
      })
      .on('mouseenter', function(event, d) {
        var n = d.data;
        var html = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
          '<div style="width:16px;height:16px;border-radius:3px;background:' + n.hex +
          ';border:1px solid rgba(255,255,255,0.3)"></div>' +
          '<strong>' + n.hex + '</strong></div>' +
          'L*=' + n.L.toFixed(2) + '&nbsp; a*=' + n.a.toFixed(2) + '&nbsp; b*=' + n.b.toFixed(2) + '<br>' +
          '\\u0394E to focus: ' + n.de_focus.toFixed(3) +
          (n.depth === 0 ? '<br><em style="color:var(--accent)">Focus seed</em>' :
           '<br><em style="color:var(--text-dim)">Depth ' + n.depth + ' &middot; Click to navigate</em>');
        tip.innerHTML = html;
        var wr = wrap.getBoundingClientRect();
        tip.style.left = (event.clientX - wr.left + 15) + 'px';
        tip.style.top = (event.clientY - wr.top - 10) + 'px';
        tip.classList.add('visible');

        // Highlight
        d3.select(this)
          .transition().duration(100)
          .attr('r', d.r * 1.3)
          .attr('stroke', '#ffffff')
          .attr('stroke-width', 2);
      })
      .on('mouseleave', function(event, d) {
        tip.classList.remove('visible');
        d3.select(this)
          .transition().duration(200)
          .attr('r', d.r)
          .attr('stroke', d.data.depth === 0 ? '#ffffff' :
                          d.data.depth === 1 ? 'rgba(255,255,255,0.25)' : 'none')
          .attr('stroke-width', d.data.depth === 0 ? 3 : 1.5);
      });

    // Force simulation
    var sim = d3.forceSimulation(simNodes)
      .force('x', d3.forceX(function(d) { return d.xTarget; }).strength(0.3))
      .force('y', d3.forceY(function(d) { return d.yTarget; }).strength(0.3))
      .force('collide', d3.forceCollide(function(d) { return d.r + 3; }).strength(0.8).iterations(3))
      .force('link', d3.forceLink(simEdges)
        .distance(function(d) { return 30 + (d.de / state.threshold) * 80; })
        .strength(0.05))
      .alphaDecay(0.04)
      .on('tick', function() {
        edgeEls
          .attr('x1', function(d) { return d.source.x; })
          .attr('y1', function(d) { return d.source.y; })
          .attr('x2', function(d) { return d.target.x; })
          .attr('y2', function(d) { return d.target.y; });
        nodeEls
          .attr('cx', function(d) { return d.x; })
          .attr('cy', function(d) { return d.y; });
      });
  }

  // Keyboard navigation
  document.addEventListener('keydown', function(e) {
    if (state.loading) return;
    if (e.code === 'ArrowRight' || e.code === 'Space') {
      e.preventDefault();
      if (state.offset + 1 < state.total) navigateTo(state.offset + 1);
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      if (state.offset > 0) navigateTo(state.offset - 1);
    }
  });

  // Initial load
  loadGraph(0, state.threshold, state.depth).then(function() {
    render();
    buildGraph();
  });
})();
</script>
</body>
</html>"""
