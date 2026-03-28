"""
CSV data ingestion module for the pipeline.
"""

import csv
import datetime
from target_pipeline_original import db


REQUIRED_COLUMNS = ["key", "value", "category"]


def load_csv(filepath):
    """Load a CSV file and return rows as list of dicts."""
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def validate_row(row):
    """Check row has required columns with non-empty values."""
    for col in REQUIRED_COLUMNS:
        if col not in row:
            return False
        val = row[col]
        if val is None or str(val).strip() == "":
            return False
    return True


def ingest_file(filepath):
    """
    Ingest a CSV file into the database.
    Returns list of inserted record IDs.
    N+1 read-back: after inserting each row, reads it back by ID.
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
            # N+1 read-back pattern: read each record after insert
            _readback = db.get_record_by_id(record_id)
            inserted_ids.append(record_id)
    return inserted_ids


def ingest_batch(filepaths):
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


def get_ingested_records(ids):
    """Retrieve ingested records by ID."""
    return db.get_records_by_ids(ids)


def reset_pipeline():
    """Clear all data (for testing)."""
    db.clear_all()
