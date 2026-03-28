"""
EvolveSys orchestrator — the attractor-orchestrator prompt and dispatch logic.

This module builds the master orchestration prompt that the
attractor-orchestrator agent uses to run EvolveSys.

The attractor-orchestrator is a Claude Opus 4.6 agent with access to:
- All 8 AttractorFlow MCP tools
- Task tool (to spawn explorer-agent and convergence-agent subagents)
- Bash, Read, Write tools

This module provides:
1. The master orchestration prompt (passed to attractor-orchestrator on startup)
2. The regime routing logic (in prose form — the agent interprets this)
3. CLI entry point to launch the orchestrator
"""

import json
import os
import sys
import argparse
from datetime import datetime

from evolve_sys.config import (
    CYCLES_PER_RUN,
    STEPS_BETWEEN_REGIME_CHECK,
    STEPS_BETWEEN_BIFURCATION_CHECK,
    DIVERGING_LAMBDA_THRESHOLD,
    PITCHFORK_SILHOUETTE_THRESHOLD,
)
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict
from evolve_sys.improvement_cycle import (
    RunLog,
    build_explorer_prompt,
    state_cycle_start,
)
from evolve_sys import milestones


def build_orchestrator_prompt(
    total_cycles: int,
    initial_snapshot_json: str,
    run_log_path: str,
) -> str:
    """
    Build the full prompt for the attractor-orchestrator agent.
    This is a rich, self-contained brief the orchestrator follows for the entire run.
    """
    return f"""You are the **attractor-orchestrator** for **EvolveSys** — a stability-guided autonomous code evolution engine.

## Mission
Run {total_cycles} improvement cycles on `target_pipeline/` across four quality axes:
test coverage, type safety, performance, and code complexity.

## Initial Quality Snapshot
```json
{initial_snapshot_json}
```

## The EvolveSys Loop (repeat for each cycle)

### Step 1 — Record cycle start state + milestone
```
attractorflow_record_state(
  state_text="EvolveSys cycle N starting. coverage=X%, mypy=Y, bench=Zms, cc=W",
  goal_text="Improve target_pipeline/ quality across 4 axes: test coverage, type safety, performance, code complexity"
)
```

Also record a milestone via Bash (do this after every significant event):
```bash
python -c "
import sys; sys.path.insert(0,'.')
from evolve_sys import milestones
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict
snap = measure_all(cycle=N)
milestones.cycle_start(cycle=N, step=STEP, snap_dict=snapshot_to_dict(snap))
"
```

### Step 2 — Spawn explorer-agent
Use the Task tool to invoke the **explorer-agent** subagent with the prompt from
`evolve_sys/improvement_cycle.py::build_explorer_prompt(snap, cycle)`.

The explorer-agent will:
- Scan target_pipeline/ across all 4 quality axes
- Generate 3–5 distinct improvement proposals as JSON
- Record its trajectory via attractorflow_record_state after each proposal
- Return a JSON array of proposals

Record each proposal the explorer returns:
```
attractorflow_record_state(state_text="Proposal: [title] targeting [file] for [axis]")
```

### Step 3 — Bifurcation check (every cycle, and every {STEPS_BETWEEN_BIFURCATION_CHECK} steps)
```
result = attractorflow_detect_bifurcation()
```

**If PITCHFORK detected (silhouette ≥ {PITCHFORK_SILHOUETTE_THRESHOLD}):**
- Record: `attractorflow_record_state("PITCHFORK BIFURCATION: proposals cluster into 2 independent tracks")`
- Record milestone:
  ```bash
  python -c "import sys; sys.path.insert(0,'.'); from evolve_sys import milestones; milestones.bifurcation_detected(cycle=N, step=STEP, btype='PITCHFORK', cluster_a=['perf proposals...'], cluster_b=['correctness proposals...'], silhouette=SCORE)"
  ```
- Split proposals by cluster using the cluster_centroids in the result
- Record milestone for each parallel track:
  ```bash
  python -c "import sys; sys.path.insert(0,'.'); from evolve_sys import milestones; milestones.parallel_track_spawned(cycle=N, step=STEP, track_name='convergence-agent-perf', proposals=[...])"
  ```
- Spawn TWO convergence-agents in parallel using the Task tool:
  - `convergence-agent-perf`: gets the performance/optimization cluster proposals
  - `convergence-agent-correctness`: gets the test/type-safety cluster proposals
- Monitor both; wait for both to complete
- `attractorflow_checkpoint()` after both complete successfully

**If HOPF detected:**
- Add explicit exit criterion to the convergence-agent prompt:
  "Stop when `radon cc transformer.py` reports average complexity < 5"
- This converts the unbounded iteration to a bounded limit cycle

**If SADDLE_NODE detected:**
- `attractorflow_checkpoint()` to save current position
- `attractorflow_inject_perturbation(magnitude=0.7)` to escape collapsed approach
- Re-run explorer with instruction: "Previous approach collapsed. Try batch loading strategy."

**If no bifurcation:**
- Pick the single best proposal (highest estimated_impact)
- Spawn ONE convergence-agent with that proposal

### Step 4 — Regime check (every {STEPS_BETWEEN_REGIME_CHECK} steps)
```
regime_result = attractorflow_get_regime()
```

After getting regime, record a milestone (substituting actual values):
```bash
python -c "
import sys; sys.path.insert(0,'.')
from evolve_sys import milestones
milestones.regime_change(cycle=N, step=S, new_regime='REGIME', old_regime='PREV',
    confidence=0.87, lambda_value=-0.142, action='ACTION')
"
```

Act on the regime:

| Regime | Action |
|--------|--------|
| **CONVERGING** | Add to convergence-agent context: "Commit to current approach. No alternatives." |
| **EXPLORING** | Allow; monitor λ stays < 0.25 |
| **STUCK** | `attractorflow_inject_perturbation(magnitude=0.5)` + re-spawn explorer with property-based testing angle. Record: `python -c "from evolve_sys import milestones; milestones.intervention_applied(cycle=N, step=S, trigger='STUCK', action='SPAWN_EXPLORER', hint='property-based testing')"` |
| **OSCILLATING** | `attractorflow_inject_perturbation(magnitude=0.4)` + "Write a mypy test that only ONE of your two options passes". Record: `python -c "from evolve_sys import milestones; milestones.intervention_applied(cycle=N, step=S, trigger='OSCILLATING', action='BREAK_SYMMETRY', hint='mypy test asymmetry')"` |
| **DIVERGING** | `attractorflow_checkpoint()` first, then: "Stop. Re-read original proposal. Narrow scope to ONE specific change." Record: `python -c "from evolve_sys import milestones; milestones.intervention_applied(cycle=N, step=S, trigger='DIVERGING', action='RESTORE_CHECKPOINT', hint='scope narrowed')"` |
| **PLATEAU** | Add ONE specific constraint: "Your next step must make a specific test pass. Nothing else." Record: `python -c "from evolve_sys import milestones; milestones.intervention_applied(cycle=N, step=S, trigger='PLATEAU', action='NUDGE', hint='specific test target')"` |
| **CYCLING** | Continue if cycle amplitude is decreasing; if stable: `attractorflow_inject_perturbation(magnitude=0.3)` |

### Step 5 — Monitor convergence-agent(s)
For each running convergence-agent track:
- Record its progress states via attractorflow_record_state
- Check lyapunov every 3 agent steps: `attractorflow_get_lyapunov()`
- If λ trend > 0.05 in the convergence-agent: intervene (see table above)
- If λ crosses {DIVERGING_LAMBDA_THRESHOLD}: halt the track, restore checkpoint, retry with narrower scope
- Call `attractorflow_checkpoint()` when the convergence-agent reports success

### Step 6 — Measure quality delta + record milestone
After convergence complete, run:
```bash
python -m evolve_sys.quality_metrics --json
```
Compare to snapshot from Step 1. Log results to `{run_log_path}`.

Also record a quality milestone:
```bash
python -c "
import sys, json; sys.path.insert(0,'.')
from evolve_sys import milestones
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict
snap_after = measure_all(cycle=N)
milestones.quality_snapshot(cycle=N, step=STEP, snap_dict=snapshot_to_dict(snap_after),
    label='cycle_N_complete')
"
```

Record: `attractorflow_record_state("Cycle N complete. delta: coverage=[X]%, mypy=[Y], bench=[Z]ms, cc=[W]")`

### Step 7 — Loop to next cycle

## Intervention Recipes (reference)

**STUCK escape sequence:**
1. Level 1: `attractorflow_inject_perturbation(magnitude=0.3)` — add a constraint
2. Level 2: `attractorflow_inject_perturbation(magnitude=0.6)` — switch approach
3. Level 3: Re-spawn explorer with completely different angle

**OSCILLATING symmetry break:**
- Inject: "Write a test that only ONE of your two candidate implementations can pass. Run it. Choose the implementation that passes."

**DIVERGING re-anchor:**
1. `attractorflow_checkpoint()` — save current position
2. Re-read original proposal title + target file
3. Narrow scope: "Implement ONLY the first bullet of your proposal. Nothing else."

**PLATEAU nudge:**
- Do NOT inject full perturbation
- Add: "Your next action must be one specific thing: [add one type annotation | write one test | extract one function]"

## After All Cycles Complete — Generate Documentation

When all {total_cycles} cycles are done:

1. Record run completion milestone:
```bash
python -c "
import sys; sys.path.insert(0,'.')
from evolve_sys import milestones
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict
from evolve_sys.improvement_cycle import RunLog
snap = measure_all(cycle={total_cycles})
log = RunLog()
milestones.run_complete(total_cycles={total_cycles},
    final_snap_dict=snapshot_to_dict(snap),
    total_delta=log.get_total_deltas())
"
```

2. Generate the evolution report:
```bash
python -m evolve_sys.doc_generator
```

3. Display the report:
```bash
cat EVOLUTION_REPORT.md
```

4. Show the comparison (if baseline was run):
```bash
python -m evolve_sys_baseline.simple_orchestrator --compare
```

## Success Criteria
- All {total_cycles} cycles complete
- PITCHFORK bifurcation fires at least once (you'll see parallel tracks spawn)
- All 7 attractor regimes observed at least once
- Quality improves across at least 3 of the 4 axes
- `EVOLUTION_REPORT.md` generated with full numerical + visual proof

## Status Reporting
After every 5 cycles, output:
```
=== EvolveSys Progress (cycle N/{total_cycles}) ===
Coverage: [before] → [now]  ([delta])
Mypy errors: [before] → [now]
Benchmark: [before] → [now]
Avg complexity: [before] → [now]
Bifurcations: [list]
Regimes observed: [list]
```

## Files you may write
- `target_pipeline/` — any file (improvements)
- `{run_log_path}` — cycle log
- DO NOT modify: `evolve_sys/`, `.claude/`, `.mcp.json`, `attractorflow/`
"""


def print_orchestrator_prompt(cycles: int = CYCLES_PER_RUN):
    """Print the orchestrator prompt to stdout (for piping to attractor-orchestrator)."""
    snap = measure_all(cycle=0)
    log = RunLog()
    # Record run start milestone
    milestones.run_start(
        snap_dict=snapshot_to_dict(snap),
        goal="Improve target_pipeline/ quality across 4 axes: test coverage, type safety, performance, code complexity"
    )
    prompt = build_orchestrator_prompt(
        total_cycles=cycles,
        initial_snapshot_json=json.dumps(snapshot_to_dict(snap), indent=2),
        run_log_path="evolve_sys/run_log.json",
    )
    print(prompt)


def show_status():
    """Print current run status from run_log.json."""
    log = RunLog()
    deltas = log.get_total_deltas()
    bifurcations = log.get_bifurcation_history()

    if not deltas:
        print("No cycles run yet. Start with: python -m evolve_sys.orchestrator --prompt")
        return

    print(f"\n=== EvolveSys Run Status ===")
    print(f"Cycles completed: {deltas['total_cycles']} ({deltas['successful_cycles']} successful)")
    print(f"\nCumulative quality improvements:")
    print(f"  Coverage:    {deltas['coverage_total']:+.1f}%")
    print(f"  Mypy errors: {deltas['mypy_total']:+d}")
    print(f"  Benchmark:   {deltas['speed_total_ms']:+.0f}ms")
    print(f"  Complexity:  {deltas['complexity_total']:+.2f}")

    if bifurcations:
        print(f"\nBifurcations detected ({len(bifurcations)} total):")
        for b in bifurcations:
            print(f"  Cycle {b['cycle']}: {b['type']} → {b['parallel_tracks']} parallel tracks")
    else:
        print("\nNo bifurcations detected yet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EvolveSys orchestrator")
    parser.add_argument("--prompt", action="store_true",
                        help="Print orchestrator prompt (pass to attractor-orchestrator agent)")
    parser.add_argument("--status", action="store_true",
                        help="Show current run status")
    parser.add_argument("--cycles", type=int, default=CYCLES_PER_RUN,
                        help=f"Number of cycles (default: {CYCLES_PER_RUN})")
    parser.add_argument("--baseline", action="store_true",
                        help="Measure and print quality baseline")
    args = parser.parse_args()

    if args.prompt:
        print_orchestrator_prompt(args.cycles)
    elif args.status:
        show_status()
    elif args.baseline:
        snap = measure_all(cycle=0)
        print(json.dumps(snapshot_to_dict(snap), indent=2))
    else:
        parser.print_help()
