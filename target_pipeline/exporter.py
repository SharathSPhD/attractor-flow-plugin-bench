"""
Data export module for the pipeline.

Type annotations, extracted helpers for clarity.
"""

import json
import os
import datetime
from typing import List, Dict, Any, Optional


def _make_serializable(obj: Any) -> Any:
    """Convert an object to JSON-serializable form."""
    if isinstance(obj, (str, int, float, bool, list, type(None))):
        return obj
    return str(obj)


def export_json(records: List[Dict[str, Any]], output_path: str) -> int:
    """Export records to a JSON file. Returns count of records written."""
    serializable = []
    for record in records:
        clean = {}
        for k, v in record.items():
            clean[k] = _make_serializable(v)
        serializable.append(clean)

    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)

    return len(serializable)


def _escape_csv_value(val: Any) -> str:
    """Escape a value for CSV output."""
    if val is None:
        return ""
    s = str(val)
    if "," in s or '"' in s or "\n" in s:
        return '"' + s.replace('"', '""') + '"'
    return s


def export_csv(records: List[Dict[str, Any]], output_path: str) -> int:
    """Export records to a CSV file. Returns count of records written."""
    if not records:
        with open(output_path, "w") as f:
            f.write("")
        return 0

    headers = list(records[0].keys())
    lines = [",".join(headers)]
    for r in records:
        vals = [_escape_csv_value(r.get(h, "")) for h in headers]
        lines.append(",".join(vals))

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return len(records)


def _compute_numeric_stats(values: List[float]) -> Dict[str, Any]:
    """Compute statistics for numeric values."""
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
    }


def export_summary(records: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
    """Export a summary report (category counts, value stats)."""
    category_counts: Dict[str, int] = {}
    numeric_values: List[float] = []

    for record in records:
        cat = record.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

        v = record.get("value")
        if isinstance(v, (int, float)):
            numeric_values.append(float(v))

    summary: Dict[str, Any] = {
        "exported_at": datetime.datetime.now().isoformat(),
        "total_records": len(records),
        "category_breakdown": category_counts,
        "numeric_stats": _compute_numeric_stats(numeric_values),
    }

    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def export_all(records: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
    """Export records in all formats to output_dir."""
    json_path = os.path.join(output_dir, "records.json")
    csv_path = os.path.join(output_dir, "records.csv")
    summary_path = os.path.join(output_dir, "summary.json")

    export_json(records, json_path)
    export_csv(records, csv_path)
    export_summary(records, summary_path)

    return {
        "json": json_path,
        "csv": csv_path,
        "summary": summary_path,
        "count": len(records)
    }
