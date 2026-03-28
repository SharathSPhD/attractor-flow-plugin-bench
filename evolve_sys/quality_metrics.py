"""
Quality metrics measurement for target_pipeline/.

Wraps: pytest-cov, mypy, radon, cProfile.
All measurements return normalized dicts for attractor-flow state recording.
"""

import subprocess
import sys
import os
import re
import json
import time
import cProfile
import pstats
import io
import tempfile
from dataclasses import dataclass, asdict
from typing import Optional

# Paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "target_pipeline")
TESTS = os.path.join(TARGET, "tests")


@dataclass
class QualitySnapshot:
    """A complete quality measurement at one point in time."""
    coverage_pct: float
    mypy_error_count: int
    benchmark_ms: float
    avg_complexity: float
    cycle: int = 0

    def delta(self, other: "QualitySnapshot") -> dict:
        """Return improvement deltas (positive = better)."""
        return {
            "coverage_delta": self.coverage_pct - other.coverage_pct,
            "mypy_delta": other.mypy_error_count - self.mypy_error_count,   # lower is better
            "speed_delta_ms": other.benchmark_ms - self.benchmark_ms,       # lower is better
            "complexity_delta": other.avg_complexity - self.avg_complexity, # lower is better
        }

    def as_state_text(self) -> str:
        """Format as text for attractorflow_record_state."""
        return (
            f"Quality snapshot — cycle {self.cycle}: "
            f"coverage={self.coverage_pct:.1f}%, "
            f"mypy_errors={self.mypy_error_count}, "
            f"benchmark={self.benchmark_ms:.0f}ms, "
            f"avg_complexity={self.avg_complexity:.2f}"
        )


def measure_coverage() -> float:
    """
    Run pytest with coverage and return coverage percentage.
    Returns 0.0 on failure.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "--cov=target_pipeline",
             "--cov-report=json",
             "--cov-config=.coveragerc",
             "-q", "--tb=no",
             TESTS],
            capture_output=True, text=True, cwd=ROOT, timeout=60
        )
        # Parse coverage.json if it exists
        cov_json = os.path.join(ROOT, "coverage.json")
        if os.path.exists(cov_json):
            with open(cov_json) as f:
                data = json.load(f)
            return data.get("totals", {}).get("percent_covered", 0.0)

        # Fallback: parse from stdout
        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', result.stdout)
        if match:
            return float(match.group(1))

        # Try simpler output
        match = re.search(r'(\d+)%', result.stdout)
        if match:
            return float(match.group(1))

        return 0.0
    except Exception as e:
        print(f"[coverage] Error: {e}")
        return 0.0


def measure_mypy_errors() -> int:
    """
    Run mypy on target_pipeline/ and return error count.
    Returns -1 on failure.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "target_pipeline/",
             "--ignore-missing-imports",
             "--strict",
             "--no-error-summary"],
            capture_output=True, text=True, cwd=ROOT, timeout=30
        )
        output = result.stdout + result.stderr
        # Count "error:" lines
        error_lines = [l for l in output.splitlines() if ": error:" in l]
        return len(error_lines)
    except Exception as e:
        print(f"[mypy] Error: {e}")
        return -1


def measure_benchmark_ms() -> float:
    """
    Benchmark the pipeline by running a synthetic workload.
    Uses 1 warmup run (discarded) + median of 5 timed runs.
    Returns elapsed time in milliseconds.
    """
    try:
        import time as _time
        import csv as _csv
        import tempfile as _tempfile

        from target_pipeline import db, ingestor, transformer

        rows = [{"key": f"bench_key_{i}", "value": str(i * 3.14), "category": "metrics"}
                for i in range(50)]

        with _tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = _csv.DictWriter(f, fieldnames=["key", "value", "category"])
            writer.writeheader()
            writer.writerows(rows)
            csv_path = f.name

        def _run() -> float:
            db.init_db()
            db.clear_all()
            t0 = _time.perf_counter()
            ids = ingestor.ingest_file(csv_path)
            records_raw = db.get_records_by_ids(ids)
            transformer.transform_batch(records_raw)
            return (_time.perf_counter() - t0) * 1000

        _run()                                  # warmup — discard result
        samples = sorted(_run() for _ in range(5))
        os.unlink(csv_path)
        return samples[2]                       # median of 5
    except Exception as e:
        print(f"[benchmark] Error: {e}")
        return 9999.0


def measure_complexity() -> float:
    """
    Run radon cc on target_pipeline/ and return average complexity.
    Returns 99.0 on failure.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc",
             "target_pipeline/", "-a", "-s"],
            capture_output=True, text=True, cwd=ROOT, timeout=20
        )
        output = result.stdout + result.stderr
        # Parse "Average complexity: A (3.38)" — grade letter then number in parens
        match = re.search(r'Average complexity:\s*\w+\s*\(([\d.]+)\)', output)
        if match:
            return float(match.group(1))
        # Fallback: bare number
        match = re.search(r'Average complexity:\s*([\d.]+)', output)
        if match:
            return float(match.group(1))
        return 99.0
    except Exception as e:
        print(f"[radon] Error: {e}")
        return 99.0


def measure_all(cycle: int = 0) -> QualitySnapshot:
    """Take a full quality snapshot. Prints progress."""
    print("[quality] Measuring test coverage...")
    cov = measure_coverage()
    print(f"[quality]   coverage: {cov:.1f}%")

    print("[quality] Measuring mypy errors...")
    mypy = measure_mypy_errors()
    print(f"[quality]   mypy errors: {mypy}")

    print("[quality] Running benchmark...")
    bench = measure_benchmark_ms()
    print(f"[quality]   benchmark: {bench:.0f}ms")

    print("[quality] Measuring complexity...")
    cc = measure_complexity()
    print(f"[quality]   avg complexity: {cc:.2f}")

    return QualitySnapshot(
        coverage_pct=cov,
        mypy_error_count=mypy,
        benchmark_ms=bench,
        avg_complexity=cc,
        cycle=cycle,
    )


def snapshot_to_dict(snap: QualitySnapshot) -> dict:
    return asdict(snap)


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Measure target_pipeline quality")
    parser.add_argument("--bench", action="store_true", help="Benchmark only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.bench:
        ms = measure_benchmark_ms()
        if args.json:
            print(json.dumps({"benchmark_ms": ms}))
        else:
            print(f"Benchmark: {ms:.2f}ms")
    else:
        snap = measure_all()
        if args.json:
            print(json.dumps(snapshot_to_dict(snap), indent=2))
        else:
            print("\n=== Quality Baseline ===")
            print(f"  Test coverage:    {snap.coverage_pct:.1f}%")
            print(f"  Mypy errors:      {snap.mypy_error_count}")
            print(f"  Benchmark:        {snap.benchmark_ms:.0f}ms")
            print(f"  Avg complexity:   {snap.avg_complexity:.2f}")
