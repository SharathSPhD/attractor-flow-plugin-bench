# EvolveSys — Project Context

This project uses **attractor-flow** (AttractorFlow MCP) to run a stability-guided
autonomous code evolution engine on `target_pipeline/`.

## What EvolveSys Does

EvolveSys autonomously improves `target_pipeline/` across 4 quality axes:
- **Test coverage** (baseline ~25%, target 65%)
- **Type safety** (mypy strict errors, target −4)
- **Performance** (N+1 query fix, target −15% benchmark time)
- **Code complexity** (radon cc, target −1.0 avg)

The improvement loop is orchestrated by the `attractor-orchestrator` agent,
which uses AttractorFlow MCP tools to monitor trajectory health and detect
bifurcations that trigger parallel improvement tracks.

## Setup

```bash
# 1. Install dependencies
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Verify AttractorFlow MCP (if not already done)
# .mcp.json is provided by the attractor-flow plugin
# Restart Claude Code after first-time setup

# 3. Measure baseline quality
python -m evolve_sys.quality_metrics
```

## Running EvolveSys

### Single cycle (interactive, step-by-step)
Use `/evolve-cycle` in Claude Code

### Multi-cycle run (automated)
Get the orchestrator prompt and hand it to attractor-orchestrator:
```bash
python -m evolve_sys.orchestrator --prompt --cycles 5
```

### Check status
```bash
python -m evolve_sys.orchestrator --status
```
Or use `/evolve-status` in Claude Code.

## Slash Commands
- `/evolve-status` — Quality dashboard + regime + bifurcation history
- `/evolve-cycle` — Trigger one improvement cycle
- `/attractor-status` — Raw AttractorFlow regime + λ value
- `/phase-portrait` — ASCII trajectory visualization

## Available Agents (from attractor-flow plugin)
- **attractor-orchestrator** — Meta-orchestrator; drives the full EvolveSys loop
- **explorer-agent** — Proposes improvements (EXPLORING phase, λ ∈ [0.05, 0.25])
- **convergence-agent** — Implements improvements (CONVERGING phase, λ < -0.05)

## Key Files
| File | Purpose |
|------|---------|
| `evolve_sys/orchestrator.py` | Master orchestration prompt + CLI |
| `evolve_sys/improvement_cycle.py` | Cycle logic + agent prompt templates |
| `evolve_sys/quality_metrics.py` | Measure coverage/mypy/complexity/perf |
| `evolve_sys/config.py` | Targets, thresholds, cycle parameters |
| `evolve_sys/report.py` | Run report generator |
| `target_pipeline/ingestor.py` | **Intentional weakness**: N+1 DB pattern, no types |
| `target_pipeline/transformer.py` | **Intentional weakness**: high cyclomatic complexity |
| `target_pipeline/validator.py` | **Intentional weakness**: partial types, edge cases untested |
| `target_pipeline/exporter.py` | **Intentional weakness**: no types, no tests |
| `evolve_sys/run_log.json` | Cycle history (created on first run) |

## AttractorFlow MCP Tools (all 8 used by EvolveSys)
- `attractorflow_record_state` — after every agent step
- `attractorflow_get_regime` — every 4 steps
- `attractorflow_get_lyapunov` — every 3 steps in convergence phase
- `attractorflow_get_trajectory` — used by /evolve-status
- `attractorflow_get_basin_depth` — before committing improvement
- `attractorflow_detect_bifurcation` — every cycle (PITCHFORK fires parallel tracks)
- `attractorflow_inject_perturbation` — on STUCK/OSCILLATING/DIVERGING
- `attractorflow_checkpoint` — when tests pass

## Expected Attractor-Flow Dynamics
| Regime | When it appears |
|--------|----------------|
| EXPLORING | Explorer scanning quality axes |
| CONVERGING | Convergence-agent implementing improvement |
| STUCK | Agent proposes identical test repeatedly |
| OSCILLATING | Agent alternates Union[str,None] ↔ Optional[str] |
| DIVERGING | Agent rewrites whole module instead of targeted fix |
| PLATEAU | Tiny complexity reductions (radon cc: 8.0 → 7.9 → 7.85) |
| CYCLING | Healthy TDD: write test → pass → refactor |

## Bifurcation Events
| Type | When | Response |
|------|------|----------|
| PITCHFORK | Perf proposals cluster separately from correctness proposals | Spawn 2 parallel convergence-agents |
| HOPF | Direct complexity fix becomes iterative | Add exit criterion: "stop when cc < 5" |
| SADDLE_NODE | Naive caching approach collapses on cache invalidation | Checkpoint + restart with batch loading |
