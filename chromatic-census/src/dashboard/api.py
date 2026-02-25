"""Dashboard JSON API endpoints.

All endpoints are read-only — they read status.json from disk and
query the SQLite results database.
"""

import json
import logging
import sqlite3
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from starlette.responses import JSONResponse

from ..core.cielab import is_in_srgb_gamut
from ..core.delta_e import delta_e_2000

logger = logging.getLogger(__name__)

# These are set by server.py at startup
STATUS_FILE = None
DB_PATH = None

# Lazily populated cache of sRGB-gamut JND seeds
_SRGB_JND_SEEDS = None
# ΔE between adjacent chain-walk pairs, and sorted gap indices
_CHAIN_DELTAS = None
_CHAIN_GAP_OFFSETS = None


def _read_status():
    """Read the current status.json file."""
    if STATUS_FILE is None or not Path(STATUS_FILE).exists():
        return {"state": "not_started"}
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Error reading status file: {e}")
        return {"state": "error", "message": str(e)}


def _query_db(query, params=(), limit=None):
    """Run a read-only query against the results database."""
    if DB_PATH is None or not Path(DB_PATH).exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        conn.row_factory = sqlite3.Row
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.warning(f"Database query error: {e}")
        return []


async def get_status(request):
    """Return current census status."""
    return JSONResponse(_read_status())


async def get_slices(request):
    """Return per-slice summary data for charts."""
    slices = _query_db("""
        SELECT s.slice_id, s.L_value, s.valid_points, s.seeds_found,
               s.density, s.duration_seconds, t.name as tier_name, t.delta_e
        FROM slices s
        JOIN thresholds t ON t.id = s.threshold_id
        ORDER BY s.slice_id, t.delta_e
    """)
    return JSONResponse(slices)


async def get_recent_seeds(request):
    """Return most recently discovered seeds (for 'color of the moment')."""
    seeds = _query_db("""
        SELECT s.L, s.a, s.b, s.hex_srgb, s.slice_id,
               t.name as tier_name, s.discovered_at
        FROM seeds s
        JOIN thresholds t ON t.id = s.threshold_id
        ORDER BY s.id DESC
    """, limit=20)
    return JSONResponse(seeds)


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "census"})


# ---------------------------------------------------------------------------
# JND Visual Audit endpoints
# ---------------------------------------------------------------------------

def _ensure_audit_index():
    """Create a composite index for efficient L*-window queries."""
    if DB_PATH is None or not Path(DB_PATH).exists():
        return
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_seeds_threshold_L "
            "ON seeds(threshold_id, L)"
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.warning(f"Could not create audit index: {e}")


def _get_jnd_threshold_id():
    """Get the threshold_id for JND."""
    rows = _query_db("SELECT id FROM thresholds WHERE name = 'JND'")
    if rows:
        return rows[0]["id"]
    return None


def _compute_chain_walk(srgb_seeds):
    """Order seeds via greedy nearest-neighbor chain walk through ΔE2000 space.

    Algorithm:
      1. Start at seed (0, 0, 0) — black.
      2. Find 9 closest unvisited seeds by ΔE2000.
      3. Sort those 9 by ΔE ascending, append to result.
      4. Reference = last seed (farthest of the 9).
      5. Repeat until all seeds placed.

    Returns a reordered copy of srgb_seeds.
    """
    import time
    t0 = time.monotonic()

    n = len(srgb_seeds)
    L = np.array([s["L"] for s in srgb_seeds])
    a = np.array([s["a"] for s in srgb_seeds])
    b = np.array([s["b"] for s in srgb_seeds])

    tree = cKDTree(np.column_stack([L, a, b]))

    # Find the origin seed (0, 0, 0) — should be the first by id order
    origin_idx = 0
    for i in range(n):
        if L[i] == 0.0 and a[i] == 0.0 and b[i] == 0.0:
            origin_idx = i
            break

    visited = np.zeros(n, dtype=bool)
    order = [origin_idx]
    visited[origin_idx] = True
    placed = 1

    ref_L, ref_a, ref_b = L[origin_idx], a[origin_idx], b[origin_idx]
    batch_size = 9
    initial_k = 50

    while placed < n:
        remaining = n - placed
        want = min(batch_size, remaining)

        # Query KD-tree for Euclidean nearest, expanding k until we find enough unvisited
        k = min(initial_k, n)
        while True:
            _, indices = tree.query([ref_L, ref_a, ref_b], k=k)
            if k == 1:
                indices = np.array([indices])
            unvisited_mask = ~visited[indices]
            unvisited_indices = indices[unvisited_mask]
            if len(unvisited_indices) >= want or k >= n:
                break
            k = min(k * 2, n)

        # Compute ΔE2000 from reference to unvisited candidates
        cand = unvisited_indices[:max(want * 5, 50)]  # limit computation
        de = delta_e_2000(ref_L, ref_a, ref_b, L[cand], a[cand], b[cand])

        # Sort by ΔE ascending, take top `want`
        sorted_order = np.argsort(de)[:want]
        batch = cand[sorted_order]

        for idx in batch:
            order.append(idx)
            visited[idx] = True
        placed += len(batch)

        # Reference = seed in batch closest to target L* (paced dark→light)
        target_L = (placed / n) * 100.0
        best = batch[np.argmin(np.abs(L[batch] - target_L))]
        ref_L, ref_a, ref_b = L[best], a[best], b[best]

        if placed % 10000 == 0:
            elapsed = time.monotonic() - t0
            logger.info(f"Chain walk: {placed:,}/{n:,} placed ({elapsed:.1f}s)")

    elapsed = time.monotonic() - t0
    logger.info(f"Chain walk complete: {n:,} seeds ordered in {elapsed:.1f}s")

    return [srgb_seeds[i] for i in order]


def _compute_chain_deltas():
    """Precompute ΔE2000 between all adjacent chain-walk pairs."""
    global _CHAIN_DELTAS, _CHAIN_GAP_OFFSETS
    import time
    t0 = time.monotonic()

    seeds = _SRGB_JND_SEEDS
    n = len(seeds)
    if n < 2:
        _CHAIN_DELTAS = np.array([])
        _CHAIN_GAP_OFFSETS = np.array([], dtype=int)
        return

    L = np.array([s["L"] for s in seeds])
    a = np.array([s["a"] for s in seeds])
    b = np.array([s["b"] for s in seeds])

    # ΔE between seed[i] and seed[i+1] for all i
    deltas = delta_e_2000(L[:-1], a[:-1], b[:-1], L[1:], a[1:], b[1:])
    _CHAIN_DELTAS = deltas

    # Sort by ΔE descending — these are offsets of the "left" seed in each pair
    _CHAIN_GAP_OFFSETS = np.argsort(deltas)[::-1]

    elapsed = time.monotonic() - t0
    logger.info(
        f"Chain deltas: min={deltas.min():.3f}, median={np.median(deltas):.3f}, "
        f"max={deltas.max():.3f} ({elapsed:.2f}s)"
    )


def _ensure_srgb_jnd_cache():
    """Load all JND seeds, filter to sRGB gamut, order by chain walk."""
    global _SRGB_JND_SEEDS
    if _SRGB_JND_SEEDS is not None:
        return

    jnd_tid = _get_jnd_threshold_id()
    if jnd_tid is None:
        _SRGB_JND_SEEDS = []
        return

    _ensure_audit_index()

    all_jnd = _query_db(
        "SELECT id, L, a, b, hex_srgb FROM seeds WHERE threshold_id = ? ORDER BY id",
        (jnd_tid,),
    )
    if not all_jnd:
        _SRGB_JND_SEEDS = []
        return

    L_arr = np.array([s["L"] for s in all_jnd])
    a_arr = np.array([s["a"] for s in all_jnd])
    b_arr = np.array([s["b"] for s in all_jnd])
    mask = is_in_srgb_gamut(L_arr, a_arr, b_arr)

    srgb_seeds = [s for s, m in zip(all_jnd, mask) if m]
    logger.info(f"JND audit cache: {len(srgb_seeds)} sRGB seeds from {len(all_jnd)} total")

    if len(srgb_seeds) < 2:
        _SRGB_JND_SEEDS = srgb_seeds
        return

    _SRGB_JND_SEEDS = _compute_chain_walk(srgb_seeds)
    _compute_chain_deltas()


async def get_jnd_audit_seed(request):
    """Return the Nth sRGB JND seed with chain-walk neighbors."""
    _ensure_srgb_jnd_cache()

    offset = int(request.query_params.get("offset", 0))
    total = len(_SRGB_JND_SEEDS)

    if total == 0 or offset >= total:
        return JSONResponse({"seed": None, "prev": None, "next": None,
                             "total": total, "offset": offset})

    s = _SRGB_JND_SEEDS[offset]
    seed_data = {
        "id": s["id"],
        "L": round(s["L"], 4),
        "a": round(s["a"], 4),
        "b": round(s["b"], 4),
        "hex": s["hex_srgb"],
    }

    # Previous seed in chain walk
    prev_data = None
    if offset > 0:
        p = _SRGB_JND_SEEDS[offset - 1]
        de = float(delta_e_2000(s["L"], s["a"], s["b"], p["L"], p["a"], p["b"]))
        prev_data = {
            "id": p["id"],
            "L": round(p["L"], 4),
            "a": round(p["a"], 4),
            "b": round(p["b"], 4),
            "hex": p["hex_srgb"],
            "delta_e": round(de, 4),
        }

    # Next seed in chain walk
    next_data = None
    if offset + 1 < total:
        n = _SRGB_JND_SEEDS[offset + 1]
        de = float(delta_e_2000(s["L"], s["a"], s["b"], n["L"], n["a"], n["b"]))
        next_data = {
            "id": n["id"],
            "L": round(n["L"], 4),
            "a": round(n["a"], 4),
            "b": round(n["b"], 4),
            "hex": n["hex_srgb"],
            "delta_e": round(de, 4),
        }

    return JSONResponse({
        "seed": seed_data,
        "prev": prev_data,
        "next": next_data,
        "total": total,
        "offset": offset,
    })


async def get_jnd_audit_neighbors(request):
    """Return all sRGB JND seeds within ΔE2000 of a given seed.

    Query params:
        seed_id: Database ID of the reference seed
        offset: Chain-walk offset (alternative to seed_id)
        threshold: ΔE2000 radius (default 2.0)
    """
    _ensure_srgb_jnd_cache()

    threshold = float(request.query_params.get("threshold", 2.0))

    # Look up reference by offset (preferred) or seed_id
    ref = None
    offset_param = request.query_params.get("offset")
    if offset_param is not None:
        offset = int(offset_param)
        if 0 <= offset < len(_SRGB_JND_SEEDS):
            ref = _SRGB_JND_SEEDS[offset]
    else:
        seed_id = int(request.query_params.get("seed_id", 0))
        for s in _SRGB_JND_SEEDS:
            if s["id"] == seed_id:
                ref = s
                break

    if ref is None:
        return JSONResponse({"reference": None, "neighbors": [], "count": 0})

    L_ref, a_ref, b_ref = ref["L"], ref["a"], ref["b"]

    jnd_tid = _get_jnd_threshold_id()

    # L* window scales with threshold (conservative: threshold + 1.0)
    L_window = threshold + 1.0
    candidates = _query_db(
        "SELECT id, L, a, b, hex_srgb FROM seeds "
        "WHERE threshold_id = ? AND L BETWEEN ? AND ? AND id != ?",
        (jnd_tid, L_ref - L_window, L_ref + L_window, ref["id"]),
    )

    if not candidates:
        return JSONResponse({
            "reference": {"id": ref["id"], "L": round(L_ref, 4), "a": round(a_ref, 4),
                          "b": round(b_ref, 4), "hex": ref["hex_srgb"]},
            "neighbors": [],
            "count": 0,
        })

    # Filter candidates to sRGB gamut
    c_L = np.array([c["L"] for c in candidates])
    c_a = np.array([c["a"] for c in candidates])
    c_b = np.array([c["b"] for c in candidates])
    srgb_mask = is_in_srgb_gamut(c_L, c_a, c_b)

    c_L = c_L[srgb_mask]
    c_a = c_a[srgb_mask]
    c_b = c_b[srgb_mask]
    srgb_candidates = [c for c, m in zip(candidates, srgb_mask) if m]

    if len(srgb_candidates) == 0:
        return JSONResponse({
            "reference": {"id": ref["id"], "L": round(L_ref, 4), "a": round(a_ref, 4),
                          "b": round(b_ref, 4), "hex": ref["hex_srgb"]},
            "neighbors": [],
            "count": 0,
        })

    # Compute vectorized ΔE2000
    distances = delta_e_2000(L_ref, a_ref, b_ref, c_L, c_a, c_b)

    # Filter to threshold and sort
    neighbors = []
    for i, (c, de) in enumerate(zip(srgb_candidates, distances)):
        if de < threshold:
            neighbors.append({
                "id": c["id"],
                "L": round(c["L"], 4),
                "a": round(c["a"], 4),
                "b": round(c["b"], 4),
                "hex": c["hex_srgb"],
                "delta_e": round(float(de), 4),
            })

    neighbors.sort(key=lambda n: n["delta_e"])

    return JSONResponse({
        "reference": {"id": ref["id"], "L": round(L_ref, 4), "a": round(a_ref, 4),
                      "b": round(b_ref, 4), "hex": ref["hex_srgb"]},
        "neighbors": neighbors,
        "count": len(neighbors),
    })


async def get_jnd_audit_gaps(request):
    """Return the largest ΔE gaps in the chain walk.

    Query params:
        rank: which gap to return (0 = largest, 1 = 2nd largest, etc.)
        count: how many gaps to return (default 20)
    """
    _ensure_srgb_jnd_cache()

    rank = int(request.query_params.get("rank", 0))
    count = int(request.query_params.get("count", 20))

    if _CHAIN_GAP_OFFSETS is None or len(_CHAIN_GAP_OFFSETS) == 0:
        return JSONResponse({"gaps": [], "total": 0})

    total_gaps = len(_CHAIN_GAP_OFFSETS)
    start = min(rank, total_gaps)
    end = min(start + count, total_gaps)

    gaps = []
    for i in range(start, end):
        offset = int(_CHAIN_GAP_OFFSETS[i])
        gaps.append({
            "rank": i,
            "offset": offset,
            "delta_e": round(float(_CHAIN_DELTAS[offset]), 4),
            "hex_left": _SRGB_JND_SEEDS[offset]["hex_srgb"],
            "hex_right": _SRGB_JND_SEEDS[offset + 1]["hex_srgb"],
        })

    stats = {
        "min": round(float(_CHAIN_DELTAS.min()), 4),
        "median": round(float(np.median(_CHAIN_DELTAS)), 4),
        "mean": round(float(_CHAIN_DELTAS.mean()), 4),
        "max": round(float(_CHAIN_DELTAS.max()), 4),
        "total_pairs": total_gaps,
    }

    return JSONResponse({"gaps": gaps, "stats": stats})
