"""
Baseline improvement cycle — no attractor-flow instrumentation.

Same task as evolve_sys/improvement_cycle.py but:
- No attractorflow_record_state calls
- No regime monitoring
- No bifurcation detection
- No perturbation injection
- No checkpoint/restore
- Pure sequential: propose → implement → commit

This is the CONTROL GROUP. Compare its run_log_baseline.json against
evolve_sys/run_log.json to measure attractor-flow's contribution.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime

# Reuse quality metrics from evolve_sys (same measurement = fair comparison)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evolve_sys.quality_metrics import QualitySnapshot, measure_all, snapshot_to_dict
from evolve_sys.config import IMPROVEMENT_AXES, MIN_COVERAGE_GAIN, MIN_MYPY_REDUCTION


@dataclass
class BaselineCycleResult:
    cycle_number: int
    proposals_generated: int
    improvements_attempted: List[str]
    improvements_succeeded: List[str]
    quality_before: QualitySnapshot
    quality_after: QualitySnapshot
    # No: bifurcation_detected, parallel_tracks, regimes_observed, interventions_applied
    # These are absent in baseline — that's the point
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def quality_delta(self) -> dict:
        return self.quality_after.delta(self.quality_before)

    def was_successful(self) -> bool:
        delta = self.quality_delta()
        return (
            delta["coverage_delta"] >= MIN_COVERAGE_GAIN or
            delta["mypy_delta"] >= MIN_MYPY_REDUCTION or
            delta["speed_delta_ms"] >= 5.0 or
            delta["complexity_delta"] >= 0.2
        )


def build_baseline_explorer_prompt(snap: QualitySnapshot, cycle: int) -> str:
    """
    Same exploration task as EvolveSys — but no attractor-flow discipline.
    The explorer receives no λ feedback, no diversity pressure, no boundary conditions.
    It will naturally drift toward repeating similar proposals (demonstrating STUCK attractor).
    """
    axes_text = "\n".join(
        f"  - **{ax.name}**: {ax.description}" for ax in IMPROVEMENT_AXES
    )
    return f"""You are an improvement agent for a Python data pipeline. Cycle {cycle}.

## Goal
Generate 3–5 improvement proposals for `target_pipeline/` across these quality axes:
{axes_text}

## Current Quality
- Test coverage: {snap.coverage_pct:.1f}%
- Mypy errors: {snap.mypy_error_count}
- Benchmark: {snap.benchmark_ms:.0f}ms
- Avg complexity: {snap.avg_complexity:.2f}

## Files to Examine
- `target_pipeline/ingestor.py` — CSV ingestion
- `target_pipeline/transformer.py` — Data transformation
- `target_pipeline/validator.py` — Validation
- `target_pipeline/exporter.py` — Export
- `target_pipeline/db.py` — Database
- `target_pipeline/tests/test_pipeline.py` — Tests

Return a JSON array of proposals with fields: axis, title, description, target_file, estimated_impact.
"""
    # NOTE: No attractor-flow tracking. No diversity enforcement.
    # Without λ monitoring, the agent will often propose similar improvements repeatedly.


def build_baseline_convergence_prompt(proposals: list, snap: QualitySnapshot, cycle: int) -> str:
    """
    Same convergence task — but no attractor-flow discipline.
    No λ monitoring, no halt on divergence, no checkpoint on success.
    The agent may add scope, rewrite modules, or stall without correction.
    """
    proposals_text = "\n".join(
        f"  {i+1}. [{p.get('axis','?')}] {p.get('title','?')} — {p.get('target_file','?')}"
        for i, p in enumerate(proposals)
    )
    return f"""Implement these code improvements for `target_pipeline/`. Cycle {cycle}.

## Improvements to implement:
{proposals_text}

## Quality baseline:
- Coverage: {snap.coverage_pct:.1f}%, Mypy errors: {snap.mypy_error_count}
- Benchmark: {snap.benchmark_ms:.0f}ms, Complexity: {snap.avg_complexity:.2f}

Implement each improvement. Run pytest after each change.
"""
    # NOTE: No convergence discipline. Agent may:
    # - Rewrite entire modules (DIVERGING — no RESTORE_CHECKPOINT)
    # - Oscillate between implementations (OSCILLATING — no BREAK_SYMMETRY)
    # - Stall on trivial improvements (STUCK — no SPAWN_EXPLORER)
    # All of these waste cycles without producing quality gains.


class BaselineRunLog:
    """Same structure as RunLog but saved to run_log_baseline.json."""

    def __init__(self):
        self.path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evolve_sys_baseline", "run_log_baseline.json"
        )
        self.cycles: List[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.cycles = json.load(f)

    def append(self, result: BaselineCycleResult):
        self.cycles.append({
            **asdict(result),
            "quality_delta": result.quality_delta(),
            "was_successful": result.was_successful(),
            "parallel_tracks": 1,   # always 1 — no bifurcation detection
            "bifurcation_detected": False,
            "regimes_observed": [],  # not tracked
            "interventions_applied": [],  # none applied
        })
        with open(self.path, "w") as f:
            json.dump(self.cycles, f, indent=2, default=str)

    def get_total_deltas(self) -> dict:
        if not self.cycles:
            return {}
        first = self.cycles[0]
        last = self.cycles[-1]
        return {
            "coverage_total": last["quality_after"]["coverage_pct"] - first["quality_before"]["coverage_pct"],
            "mypy_total": first["quality_before"]["mypy_error_count"] - last["quality_after"]["mypy_error_count"],
            "speed_total_ms": first["quality_before"]["benchmark_ms"] - last["quality_after"]["benchmark_ms"],
            "complexity_total": first["quality_before"]["avg_complexity"] - last["quality_after"]["avg_complexity"],
            "total_cycles": len(self.cycles),
            "successful_cycles": sum(1 for c in self.cycles if c.get("was_successful")),
        }
