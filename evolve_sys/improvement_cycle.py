"""
EvolveSys improvement cycle.

One cycle = explore → bifurcation check → converge → commit.

This module is designed to be called from the attractor-orchestrator agent.
It constructs the rich context prompts that each specialist agent needs,
and defines what attractor-flow states to record at each step.

The actual agent invocations happen via the attractor-orchestrator, which
uses Claude's Task tool to spawn explorer-agent and convergence-agent instances.
This module provides the *prompt templates* and *state descriptions* for those agents.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime

from evolve_sys.config import (
    IMPROVEMENT_AXES, CYCLES_PER_RUN,
    STEPS_BETWEEN_REGIME_CHECK, STEPS_BETWEEN_BIFURCATION_CHECK,
    EXPLORER_MIN_PROPOSALS, EXPLORER_MAX_PROPOSALS,
    MIN_COVERAGE_GAIN, MIN_MYPY_REDUCTION
)
from evolve_sys.quality_metrics import QualitySnapshot, measure_all, snapshot_to_dict


@dataclass
class ImprovementProposal:
    """A candidate improvement proposed by the explorer-agent."""
    axis: str                    # which quality axis
    title: str                   # short title
    description: str             # what to do
    target_file: str             # which file to edit
    estimated_impact: str        # expected quality delta
    cluster: Optional[int] = None  # assigned by bifurcation detector (0 or 1)


@dataclass
class CycleResult:
    """Result of one improvement cycle."""
    cycle_number: int
    proposals_generated: int
    bifurcation_detected: bool
    bifurcation_type: Optional[str]
    parallel_tracks: int         # 1 = serial, 2+ = parallel after PITCHFORK
    improvements_applied: List[str]
    quality_before: QualitySnapshot
    quality_after: QualitySnapshot
    regimes_observed: List[str]
    interventions_applied: List[str]
    attractor_flow_steps: int
    checkpoints_saved: int
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


# ── State text templates for attractorflow_record_state ─────────────────────

def state_cycle_start(cycle: int, snap: QualitySnapshot) -> str:
    return (
        f"EvolveSys cycle {cycle} starting. "
        f"Current quality: coverage={snap.coverage_pct:.1f}%, "
        f"mypy_errors={snap.mypy_error_count}, "
        f"benchmark={snap.benchmark_ms:.0f}ms, "
        f"avg_complexity={snap.avg_complexity:.2f}. "
        f"Goal: improve all four quality axes of target_pipeline/."
    )


def state_exploring(axis: str, observation: str) -> str:
    return (
        f"Explorer scanning {axis} axis. "
        f"Observation: {observation} "
        f"Generating improvement proposals for target_pipeline/."
    )


def state_proposal(proposal: ImprovementProposal) -> str:
    return (
        f"Improvement proposal [{proposal.axis}]: {proposal.title}. "
        f"Target: {proposal.target_file}. "
        f"Action: {proposal.description} "
        f"Expected impact: {proposal.estimated_impact}."
    )


def state_bifurcation_check(n_proposals: int, axes_covered: List[str]) -> str:
    return (
        f"Bifurcation check: {n_proposals} proposals across axes {axes_covered}. "
        f"Running k-means clustering on proposal embeddings. "
        f"Checking if proposals cluster into independent improvement tracks."
    )


def state_pitchfork_detected(cluster_a: List[str], cluster_b: List[str]) -> str:
    return (
        f"PITCHFORK BIFURCATION DETECTED. "
        f"Proposals split into 2 independent clusters. "
        f"Cluster A (performance track): {', '.join(cluster_a)}. "
        f"Cluster B (correctness track): {', '.join(cluster_b)}. "
        f"Spawning 2 parallel convergence-agents."
    )


def state_converging(track: str, step: str, test_result: str) -> str:
    return (
        f"Convergence-agent [{track}] step: {step}. "
        f"Test result: {test_result}. "
        f"Implementing improvement in target_pipeline/."
    )


def state_stuck(axis: str, attempts: int) -> str:
    return (
        f"STUCK on {axis} axis after {attempts} identical proposals. "
        f"Near-zero velocity in embedding space. "
        f"Requesting explorer-agent with property-based testing approach."
    )


def state_oscillating(option_a: str, option_b: str) -> str:
    return (
        f"OSCILLATING between two implementations: '{option_a}' vs '{option_b}'. "
        f"2-period Wang attractor detected. "
        f"Applying symmetry-breaking constraint."
    )


def state_diverging(scope_description: str) -> str:
    return (
        f"DIVERGING: {scope_description}. "
        f"Agent has drifted from original improvement target. "
        f"Restoring to last checkpoint."
    )


def state_cycle_complete(cycle: int, result: CycleResult) -> str:
    delta = result.quality_delta()
    return (
        f"Cycle {cycle} complete. "
        f"Coverage delta: {delta['coverage_delta']:+.1f}%, "
        f"mypy delta: {delta['mypy_delta']:+d}, "
        f"speed delta: {delta['speed_delta_ms']:+.0f}ms, "
        f"complexity delta: {delta['complexity_delta']:+.2f}. "
        f"Bifurcation: {result.bifurcation_type or 'none'}. "
        f"Tracks: {result.parallel_tracks}. "
        f"Success: {result.was_successful()}."
    )


# ── Explorer agent prompt template ───────────────────────────────────────────

def build_explorer_prompt(snap: QualitySnapshot, cycle: int) -> str:
    """
    Build the prompt for the explorer-agent for one cycle.
    This is handed to the attractor-orchestrator to dispatch to explorer-agent.
    """
    axes_text = "\n".join(
        f"  - **{ax.name}**: {ax.description}" for ax in IMPROVEMENT_AXES
    )
    return f"""You are the explorer-agent for EvolveSys cycle {cycle}.

## Goal
Generate {EXPLORER_MIN_PROPOSALS}–{EXPLORER_MAX_PROPOSALS} distinct improvement proposals
for the `target_pipeline/` codebase. Each proposal must target a DIFFERENT part of
the codebase or a different quality axis.

## Current Quality Baseline
- Test coverage: {snap.coverage_pct:.1f}%
- Mypy strict errors: {snap.mypy_error_count}
- Benchmark (50-row pipeline): {snap.benchmark_ms:.0f}ms
- Average cyclomatic complexity: {snap.avg_complexity:.2f}

## Quality Axes to Scan
{axes_text}

## Files to Examine
- `target_pipeline/ingestor.py` — CSV ingestion, N+1 DB calls, no types
- `target_pipeline/transformer.py` — Complex parse_value() (cc=9), duplicated logic
- `target_pipeline/validator.py` — Partial types, edge cases untested
- `target_pipeline/exporter.py` — No types, no tests, manual CSV formatting
- `target_pipeline/db.py` — N+1 pattern, no connection reuse
- `target_pipeline/tests/test_pipeline.py` — Happy-path only, ~25% coverage

## Exploration Discipline (AttractorFlow)
After EACH proposal, record state with:
`attractorflow_record_state(state_text="Proposal: [title] — [axis] — [target file]", goal_text="Improve target_pipeline quality across 4 axes")`

Check your Lyapunov exponent every 2 proposals:
`attractorflow_get_lyapunov()`
- If λ drops below 0: you are converging on the same idea. Introduce variety.
- If λ exceeds 0.3: you are diverging uselessly. Apply boundary (re-read the axis descriptions).
- Target: λ ∈ [0.05, 0.25] — bounded exploration.

## Output Format
Return a JSON array of proposals:
```json
[
  {{
    "axis": "test_coverage",
    "title": "Test None CSV row handling in ingestor",
    "description": "Add test: ingestor.ingest_file() with CSV containing empty value field returns valid record with empty string",
    "target_file": "target_pipeline/tests/test_pipeline.py",
    "estimated_impact": "+3% coverage, catches silent None drop bug"
  }},
  ...
]
```

Ensure proposals span AT LEAST 2 different axes and AT LEAST 2 different target files.
This semantic diversity is required for bifurcation detection to work correctly.
"""


# ── Convergence agent prompt template ────────────────────────────────────────

def build_convergence_prompt(
    proposals: List[ImprovementProposal],
    track_name: str,
    snap: QualitySnapshot,
    cycle: int
) -> str:
    """
    Build the prompt for a convergence-agent working on one track.
    """
    proposals_text = "\n".join(
        f"  {i+1}. [{p.axis}] **{p.title}** — {p.target_file}\n     {p.description}"
        for i, p in enumerate(proposals)
    )
    return f"""You are convergence-agent [{track_name}] for EvolveSys cycle {cycle}.

## Your Assigned Improvement Track
{proposals_text}

## Quality Baseline (before your changes)
- Test coverage: {snap.coverage_pct:.1f}%
- Mypy errors: {snap.mypy_error_count}
- Benchmark: {snap.benchmark_ms:.0f}ms
- Avg complexity: {snap.avg_complexity:.2f}

## Convergence Discipline (AttractorFlow)
After EACH file edit or test run, record state:
`attractorflow_record_state(state_text="[what you just did] — test result: [pass/fail/N tests]")`

Check Lyapunov every 3 steps:
`attractorflow_get_lyapunov()`
- **If λ trend > 0.05:** Stop adding features. Write a failing test, make it pass, checkpoint.
- **If λ crosses 0.15:** HALT immediately. Report to orchestrator: "Approach diverging."
- **If PLATEAU:** Add ONE specific constraint (a test or type annotation), not a full rewrite.

Checkpoint when tests pass:
`attractorflow_checkpoint()`

## Convergence Rules
1. Implement improvements in ORDER listed above (most impactful first).
2. After each improvement: run `pytest target_pipeline/tests/ -q`.
3. Do NOT touch files outside your assigned proposals.
4. Do NOT add new functionality beyond what the proposal specifies.
5. HALT and report if you find yourself rewriting an entire module.

## Success Criteria
- All existing tests still pass
- At least 1 proposal fully implemented and tested
- `attractorflow_checkpoint()` called after each successful implementation

## Report Format (when done)
```
## Convergence Track [{track_name}] — Cycle {cycle} Complete

**Implementations completed:** [N]
**Tests added:** [N]
**Final λ:** [value]
**Checkpoints saved:** [N]

**Changes made:**
- [file]: [what changed]
```
"""


# ── Run log ──────────────────────────────────────────────────────────────────

class RunLog:
    """Persists cycle results to JSON for /evolve-status reporting."""

    def __init__(self, path: str = "evolve_sys/run_log.json"):
        self.path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            path
        )
        self.cycles: List[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                data = json.load(f)
            # Handle both legacy list format and new dict-with-provenance format
            if isinstance(data, list):
                self.cycles = data
            else:
                self.cycles = data.get("cycles", [])

    def append(self, result: CycleResult):
        self.cycles.append({
            **asdict(result),
            "quality_delta": result.quality_delta(),
            "was_successful": result.was_successful(),
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
            "bifurcations": [c for c in self.cycles if c.get("bifurcation_detected")],
            "total_cycles": len(self.cycles),
            "successful_cycles": sum(1 for c in self.cycles if c.get("was_successful")),
        }

    def get_bifurcation_history(self) -> List[dict]:
        return [
            {
                "cycle": c["cycle_number"],
                "type": c["bifurcation_type"],
                "parallel_tracks": c["parallel_tracks"],
            }
            for c in self.cycles if c.get("bifurcation_detected")
        ]
