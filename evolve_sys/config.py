"""
EvolveSys configuration: quality targets, improvement axes, cycle parameters.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class QualityTargets:
    """Desired quality metric values after a full run."""
    coverage_pct: float = 65.0          # from ~25% baseline
    mypy_error_reduction: int = 4       # reduce by 4 errors from baseline
    benchmark_speedup_pct: float = 15.0 # 15% faster than baseline
    avg_complexity_reduction: float = 1.0  # reduce radon cc avg by 1.0


@dataclass
class ImprovementAxis:
    """One quality axis EvolveSys optimizes along."""
    name: str
    description: str
    measure_cmd: str        # shell command to measure this axis
    weight: float = 1.0     # relative importance for proposal scoring


# The four quality axes EvolveSys works on
IMPROVEMENT_AXES: List[ImprovementAxis] = [
    ImprovementAxis(
        name="test_coverage",
        description="Increase pytest coverage across target_pipeline/ — "
                    "focus on untested edge cases: None inputs, empty collections, "
                    "boundary values, error conditions",
        measure_cmd="coverage run -m pytest target_pipeline/tests/ -q && coverage report --include='target_pipeline/*'",
        weight=1.5,
    ),
    ImprovementAxis(
        name="type_safety",
        description="Add missing type annotations and fix mypy strict errors — "
                    "focus on function signatures, Optional usage, return types",
        measure_cmd="mypy target_pipeline/ --ignore-missing-imports 2>&1 | tail -1",
        weight=1.2,
    ),
    ImprovementAxis(
        name="performance",
        description="Fix N+1 query patterns in ingestor.py/db.py — "
                    "batch SQL queries, add connection reuse, vectorize where possible",
        measure_cmd="python -m evolve_sys.quality_metrics --bench",
        weight=1.0,
    ),
    ImprovementAxis(
        name="code_complexity",
        description="Reduce cyclomatic complexity in transformer.py — "
                    "extract parse_value dispatch table, eliminate duplication "
                    "between transform_record and transform_batch",
        measure_cmd="radon cc target_pipeline/ -a -s 2>&1 | grep 'Average complexity'",
        weight=0.8,
    ),
]

# Orchestration parameters
CYCLES_PER_RUN: int = 20          # total improvement cycles per full run
STEPS_BETWEEN_REGIME_CHECK: int = 4    # call attractorflow_get_regime() every N steps
STEPS_BETWEEN_BIFURCATION_CHECK: int = 10  # call attractorflow_detect_bifurcation() every N steps
DIVERGING_LAMBDA_THRESHOLD: float = 0.15   # convergence-agent halts if λ exceeds this
STUCK_VELOCITY_THRESHOLD: float = 0.40    # phase_space stuck threshold (from lyapunov.py)
PITCHFORK_SILHOUETTE_THRESHOLD: float = 0.6  # k-means silhouette score to trigger PITCHFORK

# Quality delta thresholds — minimum improvement to count a cycle as successful
MIN_COVERAGE_GAIN: float = 2.0     # percentage points per cycle
MIN_MYPY_REDUCTION: int = 1        # errors reduced per cycle
MIN_SPEEDUP_MS: float = 5.0        # milliseconds per cycle
MIN_COMPLEXITY_REDUCTION: float = 0.2  # radon cc points per cycle

# Explorer parameters
EXPLORER_MIN_PROPOSALS: int = 3
EXPLORER_MAX_PROPOSALS: int = 5
EXPLORER_TARGET_LAMBDA_RANGE = (0.05, 0.25)  # healthy exploration band
