"""
Baseline orchestrator — the CONTROL GROUP for EvolveSys comparison.

Same task, same target, same quality axes as evolve_sys/orchestrator.py.
Difference: NO attractor-flow MCP tools. Pure sequential greedy loop.

How it differs from EvolveSys:
- No trajectory monitoring (no λ, no regime classification)
- No bifurcation detection → always serial (1 track), even when 2 would be faster
- No stuck detection → repeats same proposals if agent stalls
- No oscillation detection → wastes cycles if agent oscillates
- No divergence detection → scope creep goes unchecked
- No perturbation injection → no escape from local optima
- No checkpointing → no rollback on bad changes

Usage:
  python -m evolve_sys_baseline.simple_orchestrator --prompt --cycles 5
  python -m evolve_sys_baseline.simple_orchestrator --status
  python -m evolve_sys_baseline.simple_orchestrator --compare
"""

import json
import os
import sys
import argparse
from datetime import datetime

# Reuse quality metrics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict
from evolve_sys.config import CYCLES_PER_RUN
from evolve_sys_baseline.simple_cycle import BaselineRunLog, build_baseline_explorer_prompt


def build_baseline_orchestrator_prompt(total_cycles: int, initial_snapshot_json: str) -> str:
    """
    The baseline orchestrator prompt — given to a plain Claude agent (no attractor-orchestrator).
    No AttractorFlow MCP tools. No regime routing. No bifurcation detection.

    This is deliberately simpler — and consequently less effective. That's the point.
    """
    return f"""You are a code improvement agent. Run {total_cycles} improvement cycles on `target_pipeline/`.

## Initial Quality
```json
{initial_snapshot_json}
```

## Improvement Loop (repeat {total_cycles} times)

For each cycle:

1. **Explore**: Read target_pipeline/ and identify improvements across:
   - Test coverage (add missing tests)
   - Type safety (add missing type annotations, fix mypy errors)
   - Performance (fix inefficient patterns)
   - Code complexity (simplify complex functions)

2. **Select**: Pick the 2 best improvements.

3. **Implement**: Make the changes. Run `pytest target_pipeline/tests/ -q` after each change.

4. **Measure**: Run `python -m evolve_sys.quality_metrics --json` and log the delta.

5. **Repeat**.

## Quality Measurement
```bash
python -m evolve_sys.quality_metrics --json
```

## Rules
- Work on target_pipeline/ files only
- Run tests after each change
- Log each cycle to evolve_sys_baseline/run_log_baseline.json:
  ```json
  {{"cycle": N, "improvements": [...], "quality_before": {{}}, "quality_after": {{}}}}
  ```

## No special tools
You have no AttractorFlow monitoring. Make your best judgment at each step.
If you feel stuck, try a different file. If something isn't working, move on.
"""


def show_baseline_status():
    log = BaselineRunLog()
    deltas = log.get_total_deltas()
    if not deltas:
        print("No baseline cycles run yet.")
        return
    print(f"\n=== Baseline Run Status (no attractor-flow) ===")
    print(f"Cycles: {deltas['total_cycles']} ({deltas['successful_cycles']} successful)")
    print(f"Coverage:    {deltas['coverage_total']:+.1f}%")
    print(f"Mypy errors: {deltas['mypy_total']:+d}")
    print(f"Benchmark:   {deltas['speed_total_ms']:+.0f}ms")
    print(f"Complexity:  {deltas['complexity_total']:+.2f}")
    print(f"\nNote: 0 bifurcations, 0 parallel tracks, 0 interventions (by design)")


def compare_runs():
    """Compare baseline vs attractor-flow run side by side."""
    from evolve_sys.improvement_cycle import RunLog

    baseline_log = BaselineRunLog()
    af_log = RunLog()

    bd = baseline_log.get_total_deltas()
    ad = af_log.get_total_deltas()

    if not bd and not ad:
        print("No runs completed yet for either system.")
        return

    print("\n" + "=" * 65)
    print("  EvolveSys vs Baseline — Head-to-Head Comparison")
    print("=" * 65)
    print(f"{'Metric':<28} {'Baseline':>14} {'AttractorFlow':>14}")
    print("-" * 65)

    def fmt(val, unit=""):
        if val is None:
            return "N/A"
        return f"{val:+.1f}{unit}"

    if bd and ad:
        print(f"{'Test coverage gain':<28} {fmt(bd.get('coverage_total'), '%'):>14} {fmt(ad.get('coverage_total'), '%'):>14}")
        print(f"{'Mypy error reduction':<28} {fmt(bd.get('mypy_total')):>14} {fmt(ad.get('mypy_total')):>14}")
        print(f"{'Benchmark speedup (ms)':<28} {fmt(bd.get('speed_total_ms'), 'ms'):>14} {fmt(ad.get('speed_total_ms'), 'ms'):>14}")
        print(f"{'Complexity reduction':<28} {fmt(bd.get('complexity_total')):>14} {fmt(ad.get('complexity_total')):>14}")
        print("-" * 65)
        print(f"{'Total cycles':<28} {bd.get('total_cycles', 0):>14} {ad.get('total_cycles', 0):>14}")
        print(f"{'Successful cycles':<28} {bd.get('successful_cycles', 0):>14} {ad.get('successful_cycles', 0):>14}")
        print(f"{'Parallel tracks used':<28} {'0 (never)':>14} {len(ad.get('bifurcations', [])):>14}× via PITCHFORK")
        print(f"{'Bifurcations detected':<28} {'0':>14} {len(ad.get('bifurcations', [])):>14}")
        print(f"{'Interventions applied':<28} {'0':>14} {'see report':>14}")
    elif bd:
        print("Baseline complete, AttractorFlow not yet run.")
    elif ad:
        print("AttractorFlow complete, Baseline not yet run.")

    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EvolveSys Baseline (no attractor-flow)")
    parser.add_argument("--prompt", action="store_true", help="Print baseline orchestrator prompt")
    parser.add_argument("--status", action="store_true", help="Show baseline run status")
    parser.add_argument("--compare", action="store_true", help="Compare baseline vs attractor-flow")
    parser.add_argument("--cycles", type=int, default=CYCLES_PER_RUN)
    args = parser.parse_args()

    if args.prompt:
        snap = measure_all(cycle=0)
        prompt = build_baseline_orchestrator_prompt(
            total_cycles=args.cycles,
            initial_snapshot_json=json.dumps(snapshot_to_dict(snap), indent=2),
        )
        print(prompt)
    elif args.status:
        show_baseline_status()
    elif args.compare:
        compare_runs()
    else:
        parser.print_help()
