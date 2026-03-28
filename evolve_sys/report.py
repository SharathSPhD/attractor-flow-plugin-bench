"""
EvolveSys run report generator.

Reads run_log.json and produces a human-readable evolution report,
including attractor-flow regime statistics and bifurcation timeline.
"""

import json
import os
from typing import List, Dict, Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "evolve_sys", "run_log.json")


def load_log() -> List[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return json.load(f)


def generate_report(cycles: List[dict]) -> str:
    if not cycles:
        return "No cycles recorded yet."

    first = cycles[0]
    last = cycles[-1]

    # Cumulative deltas
    cov_start = first["quality_before"]["coverage_pct"]
    cov_end = last["quality_after"]["coverage_pct"]
    mypy_start = first["quality_before"]["mypy_error_count"]
    mypy_end = last["quality_after"]["mypy_error_count"]
    bench_start = first["quality_before"]["benchmark_ms"]
    bench_end = last["quality_after"]["benchmark_ms"]
    cc_start = first["quality_before"]["avg_complexity"]
    cc_end = last["quality_after"]["avg_complexity"]

    # Regime statistics
    all_regimes: List[str] = []
    for c in cycles:
        all_regimes.extend(c.get("regimes_observed", []))
    regime_counts: Dict[str, int] = {}
    for r in all_regimes:
        regime_counts[r] = regime_counts.get(r, 0) + 1

    # Interventions
    all_interventions: List[str] = []
    for c in cycles:
        all_interventions.extend(c.get("interventions_applied", []))

    # Bifurcations
    bifurcations = [c for c in cycles if c.get("bifurcation_detected")]
    pitchfork_count = sum(1 for c in bifurcations if c.get("bifurcation_type") == "PITCHFORK")
    hopf_count = sum(1 for c in bifurcations if c.get("bifurcation_type") == "HOPF")
    saddle_count = sum(1 for c in bifurcations if c.get("bifurcation_type") == "SADDLE_NODE")

    successful = sum(1 for c in cycles if c.get("was_successful"))

    lines = [
        "=" * 60,
        "EvolveSys Run Report",
        "=" * 60,
        "",
        f"Total cycles: {len(cycles)}  |  Successful: {successful}",
        "",
        "── Quality Evolution ──────────────────────────────────────",
        f"  Test coverage:  {cov_start:.1f}% → {cov_end:.1f}%  ({cov_end - cov_start:+.1f}%)",
        f"  Mypy errors:    {mypy_start} → {mypy_end}  ({mypy_end - mypy_start:+d})",
        f"  Benchmark:      {bench_start:.0f}ms → {bench_end:.0f}ms  ({bench_end - bench_start:+.0f}ms)",
        f"  Avg complexity: {cc_start:.2f} → {cc_end:.2f}  ({cc_end - cc_start:+.2f})",
        "",
        "── Attractor-Flow Dynamics ────────────────────────────────",
    ]

    if regime_counts:
        lines.append("  Regimes observed:")
        for regime, count in sorted(regime_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"    {regime:<15} {bar} ({count}×)")
    else:
        lines.append("  No regime data recorded.")

    lines.append("")
    lines.append("── Bifurcation Timeline ───────────────────────────────────")
    if bifurcations:
        for b in bifurcations:
            btype = b.get("bifurcation_type", "UNKNOWN")
            cyc = b.get("cycle_number", "?")
            tracks = b.get("parallel_tracks", 1)
            lines.append(f"  Cycle {cyc:>3}: {btype:<12} → {tracks} parallel track(s)")
        lines.append("")
        lines.append(f"  Summary: {pitchfork_count}× PITCHFORK, {hopf_count}× HOPF, {saddle_count}× SADDLE_NODE")
    else:
        lines.append("  No bifurcations detected.")

    if all_interventions:
        lines.append("")
        lines.append("── Interventions Applied ──────────────────────────────────")
        intervention_counts: Dict[str, int] = {}
        for iv in all_interventions:
            intervention_counts[iv] = intervention_counts.get(iv, 0) + 1
        for iv, count in sorted(intervention_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {iv:<30} {count}×")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    cycles = load_log()
    print(generate_report(cycles))
