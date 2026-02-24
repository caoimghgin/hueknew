# Chromatic Census

A rigorous computational enumeration of human-distinguishable colors using CIELAB space and CIEDE2000.

## Overview

Greedy sphere-packing in CIELAB color space at three perceptual thresholds (JND=1.0, Acceptability=2.0, Obvious=5.0). Runs for 2-4 weeks on darkstar. Includes a live web dashboard on port 8084.

## Key Files

- `run.py` — Main entry point. CLI: `--mode coarse|fine`, `--resume`, `--status`, `--dashboard-only`
- `config.yaml` — All runtime configuration
- `src/core/delta_e.py` — CIEDE2000 implementation (the computational bottleneck)
- `src/engine/packer.py` — Greedy sphere-packing algorithm (the heart of the project)
- `src/persistence/checkpoint.py` — Crash-resilient state for multi-week runs
- `src/dashboard/page.py` — Self-contained HTML dashboard

## Production: darkstar.acre

- **Server**: `darkstar.acre` (TrueNAS SCALE, `10.0.0.108`, AMD Ryzen 5 5600, 63GB RAM)
- **Container**: `census`
- **Image**: `caoimghgin/census:latest`
- **Port**: 8084 (dashboard)
- **Data**: `/mnt/orion/betelgeuse/Applications/census`

### Port Allocation on darkstar.acre

| Service | Port |
|---------|------|
| Oracle MCP | 8080 |
| Oracle/Chronicle Qdrant | 6333 |
| LOGOS MCP | 8082 |
| Chronicle MCP | 8083 |
| **Census Dashboard** | **8084** |

### Build & Deploy

```bash
# Build and push
docker buildx build --platform linux/amd64 -t caoimghgin/census:latest --push -f deploy/Dockerfile .

# Deploy
ssh admin@darkstar.acre "docker pull caoimghgin/census:latest && \
  docker stop census 2>/dev/null; docker rm census 2>/dev/null; \
  docker run -d --name census \
    --restart on-failure \
    --cpus='4' --memory=8g \
    -p 8084:8084 \
    -v /mnt/orion/betelgeuse/Applications/census:/app/output \
    caoimghgin/census:latest"
```

### Verify

```bash
curl http://10.0.0.108:8084/health
ssh admin@darkstar.acre "docker logs census --tail 20"
```

### Dashboard

Browse to `http://darkstar.acre:8084` for live progress.

## Running Locally

```bash
# Install deps
pip install -r requirements.txt

# Coarse grid (~2 hours, validates pipeline)
python run.py --mode coarse

# Fine grid (2-4 weeks, the real run)
python run.py --mode fine

# Resume after interruption
python run.py --resume

# Check status
python run.py --status

# Dashboard only (no engine)
python run.py --dashboard-only
```
