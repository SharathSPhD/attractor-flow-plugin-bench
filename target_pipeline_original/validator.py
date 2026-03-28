"""
Data validation module for the pipeline.

Partial type annotations, nested logic, no extracted helpers.
"""


VALID_CATEGORIES = frozenset([
    "metrics", "scores", "counts", "measurements",
    "labels", "descriptions", "tags", "notes",
    "mixed", "unknown"
])

NUMERIC_CATEGORIES = frozenset(["metrics", "scores", "counts", "measurements"])

MAX_KEY_LENGTH = 128
MAX_VALUE_LENGTH = 1000


def validate_key(key) -> bool:
    """Validate a record key."""
    if not isinstance(key, str):
        return False
    return 0 < len(key) <= MAX_KEY_LENGTH


def validate_category(category) -> bool:
    """Validate category against allowed set."""
    if category is None:
        return False
    return category in VALID_CATEGORIES


def validate_value(value, category=None) -> bool:
    """Validate a value, optionally checking against category constraints."""
    if value is None:
        if category in NUMERIC_CATEGORIES:
            return False
        else:
            return True
    elif isinstance(value, str):
        if len(value) > MAX_VALUE_LENGTH:
            return False
        else:
            return True
    elif isinstance(value, (int, float)):
        return True
    else:
        return False


def validate_record(record) -> bool:
    """Validate a transformed record dict -- nested inline checks."""
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


def validate_batch(records) -> list:
    """Validate a list of records. Returns list of (record, is_valid) tuples."""
    return [(record, validate_record(record)) for record in records]


def get_valid_records(records) -> list:
    """Filter to only valid records."""
    return [r for r, valid in validate_batch(records) if valid]


def get_invalid_records(records) -> list:
    """Filter to only invalid records."""
    return [r for r, valid in validate_batch(records) if not valid]
