"""
Milestone recorder for EvolveSys.

Records key events to milestones.jsonl so the final documentation
can reconstruct exactly how attractor-flow steered the evolution.

Event types:
  RUN_START           — first quality snapshot, goal set
  CYCLE_START         — beginning of a new improvement cycle
  EXPLORING           — explorer-agent scanning quality axes
  PROPOSAL_GENERATED  — explorer produced a candidate improvement
  BIFURCATION_CHECK   — bifurcation detector invoked
  PITCHFORK_DETECTED  — proposals split into 2 semantic clusters
  HOPF_DETECTED       — direct convergence → iterative transition
  SADDLE_NODE_DETECTED — approach collapsed, restart required
  CONVERGING          — convergence-agent making progress
  REGIME_CHANGE       — attractor-flow regime transitioned
  STUCK_DETECTED      — near-zero velocity, explorer spawned
  OSCILLATING_DETECTED — 2-period Wang attractor, symmetry break applied
  DIVERGING_DETECTED  — λ > 0.25, checkpoint restored
  PLATEAU_DETECTED    — slow drift, nudge applied
  INTERVENTION        — any attractor-flow intervention applied
  CHECKPOINT_SAVED    — attractor-flow checkpoint recorded
  QUALITY_SNAPSHOT    — quality measurement taken
  PARALLEL_TRACK_SPAWNED — new convergence-agent track created
  PARALLEL_TRACKS_MERGED — both tracks complete, results merged
  CYCLE_COMPLETE      — cycle finished, quality delta measured
  RUN_COMPLETE        — all cycles done, final state
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MILESTONES_PATH = os.path.join(ROOT, "evolve_sys", "milestones.jsonl")


@dataclass
class Milestone:
    event_type: str
    cycle: int
    step: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    lambda_value: Optional[float] = None
    regime: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


def record(
    event_type: str,
    cycle: int = 0,
    step: int = 0,
    lambda_value: Optional[float] = None,
    regime: Optional[str] = None,
    **data
) -> Milestone:
    """Record a milestone event to milestones.jsonl."""
    ms = Milestone(
        event_type=event_type,
        cycle=cycle,
        step=step,
        lambda_value=lambda_value,
        regime=regime,
        data=data,
    )
    with open(MILESTONES_PATH, "a") as f:
        f.write(json.dumps(asdict(ms)) + "\n")
    return ms


def load_all() -> List[dict]:
    """Load all milestones from milestones.jsonl."""
    if not os.path.exists(MILESTONES_PATH):
        return []
    milestones = []
    with open(MILESTONES_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    milestones.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return milestones


def clear():
    """Clear milestones (for fresh run)."""
    if os.path.exists(MILESTONES_PATH):
        os.unlink(MILESTONES_PATH)


def get_lambda_series() -> List[tuple]:
    """Return list of (step_global, lambda_value) for all recorded λ values."""
    series = []
    step_counter = 0
    for ms in load_all():
        step_counter += 1
        lv = ms.get("lambda_value")
        if lv is not None:
            series.append((step_counter, ms["cycle"], lv))
    return series


def get_regime_timeline() -> List[dict]:
    """Return regime transitions in order."""
    timeline = []
    last_regime = None
    for ms in load_all():
        r = ms.get("regime")
        if r and r != last_regime:
            timeline.append({
                "cycle": ms["cycle"],
                "step": ms["step"],
                "regime": r,
                "timestamp": ms["timestamp"],
            })
            last_regime = r
    return timeline


def get_bifurcation_events() -> List[dict]:
    """Return all bifurcation detection events."""
    bifurcation_types = {"PITCHFORK_DETECTED", "HOPF_DETECTED", "SADDLE_NODE_DETECTED"}
    return [ms for ms in load_all() if ms["event_type"] in bifurcation_types]


def get_intervention_events() -> List[dict]:
    """Return all intervention events."""
    intervention_types = {
        "STUCK_DETECTED", "OSCILLATING_DETECTED", "DIVERGING_DETECTED",
        "PLATEAU_DETECTED", "INTERVENTION"
    }
    return [ms for ms in load_all() if ms["event_type"] in intervention_types]


def get_quality_snapshots() -> List[dict]:
    """Return quality snapshots in order."""
    return [ms for ms in load_all() if ms["event_type"] == "QUALITY_SNAPSHOT"]


# ── Convenience recorders ────────────────────────────────────────────────────

def run_start(snap_dict: dict, goal: str):
    record("RUN_START", cycle=0, step=0,
           quality_snapshot=snap_dict, goal=goal)


def cycle_start(cycle: int, step: int, snap_dict: dict):
    record("CYCLE_START", cycle=cycle, step=step, quality_snapshot=snap_dict)


def proposal_generated(cycle: int, step: int, axis: str, title: str, target_file: str,
                        lambda_value: Optional[float] = None, regime: Optional[str] = None):
    record("PROPOSAL_GENERATED", cycle=cycle, step=step,
           lambda_value=lambda_value, regime=regime,
           axis=axis, title=title, target_file=target_file)


def bifurcation_detected(cycle: int, step: int, btype: str, cluster_a: list, cluster_b: list,
                          silhouette: float, lambda_value: Optional[float] = None):
    event_map = {
        "PITCHFORK": "PITCHFORK_DETECTED",
        "HOPF": "HOPF_DETECTED",
        "SADDLE_NODE": "SADDLE_NODE_DETECTED",
    }
    record(event_map.get(btype, "BIFURCATION_CHECK"),
           cycle=cycle, step=step, lambda_value=lambda_value,
           bifurcation_type=btype, cluster_a=cluster_a, cluster_b=cluster_b,
           silhouette_score=silhouette)


def parallel_track_spawned(cycle: int, step: int, track_name: str, proposals: list):
    record("PARALLEL_TRACK_SPAWNED", cycle=cycle, step=step,
           track_name=track_name, proposal_count=len(proposals),
           proposal_titles=[p.get("title", "?") for p in proposals])


def regime_change(cycle: int, step: int, new_regime: str, old_regime: Optional[str],
                   confidence: float, lambda_value: float, action: str):
    record("REGIME_CHANGE", cycle=cycle, step=step,
           regime=new_regime, lambda_value=lambda_value,
           old_regime=old_regime, confidence=confidence, action=action)


def intervention_applied(cycle: int, step: int, trigger: str, action: str,
                          hint: str, lambda_value: Optional[float] = None):
    record("INTERVENTION", cycle=cycle, step=step, lambda_value=lambda_value,
           trigger=trigger, action=action, hint=hint)


def checkpoint_saved(cycle: int, step: int, lambda_value: Optional[float] = None):
    record("CHECKPOINT_SAVED", cycle=cycle, step=step, lambda_value=lambda_value)


def quality_snapshot(cycle: int, step: int, snap_dict: dict,
                      delta: Optional[dict] = None, label: str = ""):
    record("QUALITY_SNAPSHOT", cycle=cycle, step=step,
           quality=snap_dict, delta=delta or {}, label=label)


def cycle_complete(cycle: int, step: int, result_dict: dict):
    record("CYCLE_COMPLETE", cycle=cycle, step=step, **result_dict)


def run_complete(total_cycles: int, final_snap_dict: dict, total_delta: dict):
    record("RUN_COMPLETE", cycle=total_cycles, step=0,
           final_quality=final_snap_dict, total_delta=total_delta)
