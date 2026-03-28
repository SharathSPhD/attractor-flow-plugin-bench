"""
SQLite database wrapper for the pipeline.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline.db")


def init_db():
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


def insert_record(key, value, category):
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


def get_record_by_id(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_records_by_ids(ids):
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


def mark_processed(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE records SET processed = 1 WHERE id = ?",
        (record_id,)
    )
    conn.commit()
    conn.close()


def log_audit(record_id, action, timestamp):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (record_id, action, timestamp) VALUES (?, ?, ?)",
        (record_id, action, timestamp)
    )
    conn.commit()
    conn.close()


def get_all_unprocessed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE processed = 0")
    rows = cursor.fetchall()
    conn.close()
    return rows


def clear_all():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records")
    cursor.execute("DELETE FROM audit_log")
    conn.commit()
    conn.close()
