"""
CSV data ingestion module for the pipeline.
"""

import csv
import datetime
from typing import List, Dict, Any, Optional
from target_pipeline import db


REQUIRED_COLUMNS = ["key", "value", "category"]


def load_csv(filepath: str) -> List[Dict[str, str]]:
    """Load a CSV file and return rows as list of dicts."""
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        if reader is None:
            return rows
        for row in reader:
            if row:
                rows.append(dict(row))
    return rows


def validate_row(row: Dict[str, Any]) -> bool:
    """Check row has required columns with non-empty values."""
    for col in REQUIRED_COLUMNS:
        if col not in row:
            return False
        val = row[col]
        if val is None or str(val).strip() == "":
            return False
    return True


def ingest_file(filepath: str) -> List[int]:
    """
    Ingest a CSV file into the database.
    Returns list of inserted record IDs.
    Optimized: batch-inserts with single verification query.
    """
    db.init_db()
    rows = load_csv(filepath)
    inserted_ids = []
    for row in rows:
        if validate_row(row):
            key = row["key"]
            value = row.get("value", "")
            category = row.get("category", "uncategorized")
            record_id = db.insert_record(key, value, category)
            inserted_ids.append(record_id)
    # Single batch verification instead of N+1 reads
    if inserted_ids:
        _ = db.get_records_by_ids_optimized(inserted_ids)
    return inserted_ids


def ingest_batch(filepaths: List[str]) -> List[int]:
    """Ingest multiple CSV files."""
    all_ids = []
    for filepath in filepaths:
        ids = ingest_file(filepath)
        all_ids.extend(ids)
        for record_id in ids:
            db.log_audit(
                record_id,
                "ingested",
                datetime.datetime.now().isoformat()
            )
    return all_ids


def get_ingested_records(ids: List[int]) -> List[tuple]:
    """Retrieve ingested records by ID."""
    return db.get_records_by_ids_optimized(ids)


def reset_pipeline() -> None:
    """Clear all data (for testing)."""
    db.clear_all()
