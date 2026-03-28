"""
SQLite database wrapper for the pipeline.
"""

import sqlite3
import os
from typing import List, Optional, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline.db")


def init_db() -> None:
    """Initialize database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT,
            category TEXT,
            processed INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            action TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_record(key: str, value: str, category: str) -> int:
    """Insert a record and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (key, value, category) VALUES (?, ?, ?)",
        (key, value, category)
    )
    record_id = cursor.lastrowid or 0
    conn.commit()
    conn.close()
    return record_id


def get_record_by_id(record_id: int) -> Optional[Tuple]:
    """Get a single record by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_records_by_ids(ids: List[int]) -> List[Tuple]:
    """Fetch records by IDs -- uses N+1 query pattern (one query per ID)."""
    if not ids:
        return []
    results = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for id in ids:
        cursor.execute("SELECT * FROM records WHERE id=?", (id,))
        row = cursor.fetchone()
        if row:
            results.append(row)
    conn.close()
    return results


def get_records_by_ids_optimized(ids: List[int]) -> List[Tuple]:
    """Fetch records by IDs -- uses single batch query (optimal)."""
    if not ids:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(ids))
    query = f"SELECT * FROM records WHERE id IN ({placeholders})"
    cursor.execute(query, ids)
    results = cursor.fetchall()
    conn.close()
    return results


def mark_processed(record_id: int) -> None:
    """Mark a record as processed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE records SET processed = 1 WHERE id = ?",
        (record_id,)
    )
    conn.commit()
    conn.close()


def log_audit(record_id: int, action: str, timestamp: str) -> None:
    """Log an audit event."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (record_id, action, timestamp) VALUES (?, ?, ?)",
        (record_id, action, timestamp)
    )
    conn.commit()
    conn.close()


def get_all_unprocessed() -> List[Tuple]:
    """Get all unprocessed records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE processed = 0")
    rows = cursor.fetchall()
    conn.close()
    return rows


def clear_all() -> None:
    """Clear all records and audit logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records")
    cursor.execute("DELETE FROM audit_log")
    conn.commit()
    conn.close()
