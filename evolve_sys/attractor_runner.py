"""
attractor_runner.py — Python-driven EvolveSys loop with genuine MCP calls.

Replaces the prompt-only orchestration approach. AttractorFlow monitoring is
Python-native (real server responses with real timestamps). Code generation
still uses a Claude agent prompt (stub provided below — fill in before use).

Usage:
    python -m evolve_sys.attractor_runner --cycles 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from typing import Any

from evolve_sys.config import CYCLES_PER_RUN
from evolve_sys.mcp_client import AttractorFlowClient
from evolve_sys.quality_metrics import measure_all, snapshot_to_dict

# Path for this runner's output — separate from run_log.json (legacy)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_LOG_PATH = os.path.join(ROOT, "evolve_sys", "run_log_attractor.json")


def _load_log() -> list[dict[str, Any]]:
    if os.path.exists(RUN_LOG_PATH):
        with open(RUN_LOG_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    return []


def _save_log(cycles: list[dict[str, Any]]) -> None:
    with open(RUN_LOG_PATH, "w") as f:
        json.dump(cycles, f, indent=2, default=str)


async def run_cycles(n_cycles: int) -> None:
    """
    Run n_cycles improvement cycles with genuine AttractorFlow MCP monitoring.

    Each cycle:
    1. Measures quality before (Python)
    2. Calls MCP tools in Python — real server responses logged
    3. [Code generation placeholder — wire to Claude agent before using]
    4. Measures quality after (Python)
    5. Appends real MCP responses to run_log_attractor.json
    """
    cycles_log = _load_log()

    async with AttractorFlowClient() as af:
        snap0 = measure_all(cycle=0)
        print(f"Baseline: coverage={snap0.coverage_pct:.1f}%  mypy={snap0.mypy_error_count}"
              f"  bench={snap0.benchmark_ms:.0f}ms  cc={snap0.avg_complexity:.2f}")

        await af.record_state(
            snap0.as_state_text(),
            goal_text="Improve target_pipeline/ on 4 quality axes: coverage, mypy, performance, complexity",
        )

        for cycle in range(1, n_cycles + 1):
            snap_pre = measure_all(cycle=cycle)
            ts_start = datetime.now().isoformat()

            # ── Real MCP tool calls ──────────────────────────────────────────
            await af.record_state(
                f"Cycle {cycle} start. {snap_pre.as_state_text()}",
                goal_text="Improve target_pipeline/",
            )
            bifurcation = await af.detect_bifurcation()
            regime = await af.get_regime()
            lyapunov = await af.get_lyapunov()

            print(f"\nCycle {cycle} — ftle={lyapunov.get('ftle', 0):.4f}  "
                  f"regime={regime.get('regime', '?')}  "
                  f"bifurcation={bifurcation.get('detected', False)}")

            # ── Code generation placeholder ──────────────────────────────────
            # TODO: wire this to a Claude agent prompt
            # from evolve_sys.improvement_cycle import build_explorer_prompt, build_convergence_prompt
            # explorer_prompt = build_explorer_prompt(snap_pre, cycle)
            # ... invoke Claude agent with explorer_prompt ...
            # ... invoke Claude agent with convergence_prompt ...
            print(f"  [Code generation stub — wire to Claude agent before using]")

            snap_post = measure_all(cycle=cycle)
            await af.record_state(f"Cycle {cycle} complete. {snap_post.as_state_text()}")
            ckpt = await af.checkpoint()

            delta = snap_post.delta(snap_pre)
            print(f"  Δcoverage={delta['coverage_delta']:+.1f}%  "
                  f"Δmypy={delta['mypy_delta']:+d}  "
                  f"Δbench={delta['speed_delta_ms']:+.1f}ms  "
                  f"Δcc={delta['complexity_delta']:+.2f}")

            # ── Log actual server responses — no synthesised values ──────────
            cycles_log.append({
                "cycle": cycle,
                "timestamp": ts_start,
                "quality_before": snapshot_to_dict(snap_pre),
                "quality_after": snapshot_to_dict(snap_post),
                "quality_delta": delta,
                "mcp_responses": {
                    "bifurcation": bifurcation,
                    "regime": regime,
                    "lyapunov": lyapunov,
                    "checkpoint": ckpt,
                },
            })
            _save_log(cycles_log)

    print(f"\nRun complete. Log saved to {RUN_LOG_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EvolveSys attractor runner (genuine MCP)")
    parser.add_argument("--cycles", type=int, default=CYCLES_PER_RUN,
                        help=f"Number of cycles (default: {CYCLES_PER_RUN})")
    args = parser.parse_args()
    asyncio.run(run_cycles(args.cycles))
