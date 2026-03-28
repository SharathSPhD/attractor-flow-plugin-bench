"""
Data transformation module for the pipeline.

Monolithic version with high cyclomatic complexity -- no extracted helpers.
"""

import re


NUMERIC_CATEGORIES = ["metrics", "scores", "counts", "measurements"]
TEXT_CATEGORIES = ["labels", "descriptions", "tags", "notes"]
VALID_CATEGORIES = NUMERIC_CATEGORIES + TEXT_CATEGORIES + ["mixed", "unknown"]


def parse_value(raw_value, category):
    """
    Parse a raw string value based on category.
    Monolithic function handling all category types inline.
    """
    if raw_value is None:
        return None

    if category in NUMERIC_CATEGORIES:
        # Numeric parsing -- all inline
        if isinstance(raw_value, int):
            return raw_value
        elif isinstance(raw_value, float):
            if raw_value != raw_value:  # NaN
                return 0.0
            return max(-1e9, min(1e9, raw_value))
        elif isinstance(raw_value, str):
            stripped = raw_value.strip()
            if stripped == "":
                return 0
            if stripped.startswith("0x"):
                try:
                    return int(stripped, 16)
                except ValueError:
                    return 0
            if "." in stripped or "e" in stripped.lower():
                try:
                    return float(stripped)
                except ValueError:
                    return 0.0
            else:
                try:
                    return int(stripped)
                except ValueError:
                    return 0
        else:
            return 0
    elif category in TEXT_CATEGORIES:
        # Text parsing
        if raw_value is None:
            return ""
        value_str = str(raw_value).strip()
        value_str = re.sub(r'\s+', ' ', value_str)
        if len(value_str) > 500:
            return value_str[:500] + "..."
        return value_str
    elif category == "mixed":
        # Mixed: try numeric first, fallback to text
        text = str(raw_value).strip()
        try:
            if "." in text:
                return float(text)
            return int(text)
        except (ValueError, TypeError):
            return str(raw_value).strip() if raw_value is not None else ""
    else:
        # Fallback for unknown categories
        return str(raw_value) if raw_value is not None else ""


def normalize_key(key):
    """Normalize a record key to a canonical form."""
    if not key:
        return "unknown"
    key_str = str(key).lower()
    key_str = re.sub(r'[^a-z0-9_]', '_', key_str)
    key_str = re.sub(r'_+', '_', key_str)
    key_str = key_str.strip('_')
    if not key_str:
        return "unknown"
    return key_str


def transform_record(record):
    """
    Transform a single raw DB record tuple into a clean dict.
    Input: (id, key, value, category, processed)
    """
    if record is None:
        return None

    record_id, key, raw_value, category, processed = record

    if category not in VALID_CATEGORIES:
        category = "unknown"

    parsed_value = parse_value(raw_value, category)

    tags = []
    if category in NUMERIC_CATEGORIES:
        tags.append("numeric")
        if isinstance(parsed_value, float):
            tags.append("float")
        elif isinstance(parsed_value, int):
            tags.append("integer")
    elif category in TEXT_CATEGORIES:
        tags.append("text")
        if parsed_value and len(str(parsed_value)) > 100:
            tags.append("long-text")

    return {
        "id": record_id,
        "key": normalize_key(key),
        "value": parsed_value,
        "category": category,
        "tags": tags,
        "processed": bool(processed),
    }


def transform_batch(records):
    """Transform a list of raw DB record tuples."""
    results = []
    for record in records:
        transformed = transform_record(record)
        if transformed is not None:
            results.append(transformed)
    return results
