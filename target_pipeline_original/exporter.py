"""
Data export module for the pipeline.

No type annotations, flat inline logic, no extracted helpers.
"""

import json
import os
import datetime


def export_json(records, output_path):
    """Export records to a JSON file. Returns count of records written."""
    serializable = []
    for record in records:
        clean = {}
        for k, v in record.items():
            if isinstance(v, (str, int, float, bool, list)) or v is None:
                clean[k] = v
            else:
                clean[k] = str(v)
        serializable.append(clean)

    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)

    return len(serializable)


def export_csv(records, output_path):
    """Export records to a CSV file. Returns count of records written."""
    if not records:
        with open(output_path, "w") as f:
            f.write("")
        return 0

    headers = list(records[0].keys())
    lines = [",".join(headers)]
    for r in records:
        vals = []
        for h in headers:
            val = r.get(h, "")
            if val is None:
                vals.append("")
            else:
                vals.append(str(val))
        lines.append(",".join(vals))

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return len(records)


def export_summary(records, output_path):
    """Export a summary report (category counts, value stats)."""
    # Count categories inline
    category_counts = {}
    for record in records:
        cat = record.get("category", "unknown")
        if cat in category_counts:
            category_counts[cat] = category_counts[cat] + 1
        else:
            category_counts[cat] = 1

    # Collect numeric values inline
    numeric_values = []
    for r in records:
        v = r.get("value")
        if isinstance(v, (int, float)):
            numeric_values.append(float(v))

    # Compute stats inline
    if numeric_values:
        numeric_stats = {
            "count": len(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
        }
    else:
        numeric_stats = {"count": 0, "min": None, "max": None, "avg": None}

    summary = {
        "exported_at": datetime.datetime.now().isoformat(),
        "total_records": len(records),
        "category_breakdown": category_counts,
        "numeric_stats": numeric_stats,
    }

    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def export_all(records, output_dir):
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
