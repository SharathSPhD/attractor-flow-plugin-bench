"""
Data validation module for the pipeline.

Complete type annotations, extracted helpers.
"""

from typing import Any, Optional, Dict, List, Tuple


VALID_CATEGORIES = frozenset([
    "metrics", "scores", "counts", "measurements",
    "labels", "descriptions", "tags", "notes",
    "mixed", "unknown"
])

NUMERIC_CATEGORIES = frozenset(["metrics", "scores", "counts", "measurements"])

MAX_KEY_LENGTH = 128
MAX_VALUE_LENGTH = 1000


def validate_key(key: Any) -> bool:
    """Validate a record key."""
    if not isinstance(key, str):
        return False
    return 0 < len(key) <= MAX_KEY_LENGTH


def validate_category(category: Any) -> bool:
    """Validate category against allowed set."""
    if category is None:
        return False
    return category in VALID_CATEGORIES


def validate_value(value: Any, category: Optional[str] = None) -> bool:
    """Validate a value, optionally checking against category constraints."""
    if value is None:
        return category not in NUMERIC_CATEGORIES
    elif isinstance(value, str):
        return len(value) <= MAX_VALUE_LENGTH
    elif isinstance(value, (int, float)):
        return True
    else:
        return False


def validate_record(record: Any) -> bool:
    """Validate a transformed record dict."""
    if not isinstance(record, dict):
        return False
    if not all(k in record for k in ("key", "value", "category")):
        return False
    if not validate_key(record["key"]):
        return False
    if not validate_category(record["category"]):
        return False
    if not validate_value(record["value"], record.get("category")):
        return False
    return True


def validate_batch(records: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], bool]]:
    """Validate a list of records. Returns list of (record, is_valid) tuples."""
    return [(record, validate_record(record)) for record in records]


def get_valid_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to only valid records."""
    return [r for r, valid in validate_batch(records) if valid]


def get_invalid_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to only invalid records."""
    return [r for r, valid in validate_batch(records) if not valid]
