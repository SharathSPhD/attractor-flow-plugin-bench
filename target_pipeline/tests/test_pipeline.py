"""
Minimal happy-path tests for target_pipeline.
15 tests total, happy-path only, targeting ~42% source coverage.
"""

import os
import json
import tempfile

import pytest
from target_pipeline.transformer import parse_value, normalize_key
from target_pipeline.validator import (
    validate_key, validate_category, validate_value, validate_record
)
from target_pipeline.exporter import export_json, export_csv
from target_pipeline import db


# --- transformer tests (5 tests) ---

def test_parse_value_numeric_string():
    assert parse_value("42", "metrics") == 42


def test_parse_value_float_string():
    assert parse_value("3.14", "scores") == 3.14


def test_parse_value_text():
    result = parse_value("hello world", "labels")
    assert result == "hello world"


def test_parse_value_unknown_category():
    result = parse_value("anything", "unknown")
    assert result == "anything"


def test_normalize_key_basic():
    assert normalize_key("my_key") == "my_key"


# --- validator tests (4 tests) ---

def test_validate_key_valid():
    assert validate_key("my_key") is True


def test_validate_key_invalid():
    assert validate_key(123) is False


def test_validate_category_valid():
    assert validate_category("metrics") is True


def test_validate_value_string():
    assert validate_value("hello") is True


# --- db tests (2 tests) ---

@pytest.fixture
def clean_db():
    db.init_db()
    db.clear_all()
    yield
    db.clear_all()


def test_db_insert(clean_db):
    record_id = db.insert_record("test_key", "test_val", "metrics")
    assert isinstance(record_id, int)


def test_db_get_by_id(clean_db):
    rid = db.insert_record("k", "v", "labels")
    row = db.get_record_by_id(rid)
    assert row is not None
    assert row[1] == "k"


# --- exporter tests (2 tests) ---

def test_export_json_basic():
    records = [{"key": "a", "value": 1, "category": "metrics"}]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        count = export_json(records, path)
        assert count == 1
    finally:
        os.unlink(path)


def test_export_csv_basic():
    records = [{"key": "a", "value": "hello", "category": "labels"}]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        count = export_csv(records, path)
        assert count == 1
    finally:
        os.unlink(path)


# --- extra simple tests (2 tests) ---

def test_validate_category_invalid():
    assert validate_category("bogus") is False


def test_normalize_key_uppercase():
    assert normalize_key("MyKey") == "mykey"


# --- Additional edge case tests (exporter) ---

def test_export_json_with_special_types():
    records = [
        {"key": "a", "value": 1, "category": "metrics", "extra": None},
        {"key": "b", "value": 3.14, "category": "scores"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        count = export_json(records, path)
        assert count == 2
        with open(path) as rf:
            data = json.load(rf)
            assert len(data) == 2
    finally:
        os.unlink(path)


def test_export_csv_with_quotes():
    records = [
        {"key": "a", "value": 'hello, world', "category": "labels"},
        {"key": "b", "value": 'quote"test', "category": "labels"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        count = export_csv(records, path)
        assert count == 2
        with open(path) as rf:
            lines = rf.readlines()
            assert len(lines) >= 2
    finally:
        os.unlink(path)


def test_export_csv_empty_records():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        count = export_csv([], path)
        assert count == 0
        with open(path) as rf:
            content = rf.read()
            assert content == ""
    finally:
        os.unlink(path)


# --- Additional edge case tests (transformer) ---

def test_parse_value_scientific_notation():
    result = parse_value("1.23e-4", "metrics")
    assert isinstance(result, float)
    assert 0.0001 < result < 0.0002


def test_parse_value_hex():
    result = parse_value("0xFF", "metrics")
    assert result == 255


def test_parse_value_none():
    result = parse_value(None, "metrics")
    assert result is None


def test_parse_value_text_truncation():
    long_text = "x" * 600
    result = parse_value(long_text, "labels")
    assert len(result) <= 503  # 500 + "..."


def test_normalize_key_with_dashes():
    assert normalize_key("my-key-name") == "my_key_name"


def test_normalize_key_empty():
    assert normalize_key("") == "unknown"


def test_normalize_key_special_chars():
    assert normalize_key("@#$%") == "unknown"


# --- Additional edge case tests (validator) ---

def test_validate_key_empty():
    assert validate_key("") is False


def test_validate_key_too_long():
    long_key = "k" * 200
    assert validate_key(long_key) is False


def test_validate_value_too_long():
    long_val = "v" * 1100
    assert validate_value(long_val) is False


def test_validate_record_missing_fields():
    record = {"key": "a", "value": 1}  # missing category
    assert validate_record(record) is False


def test_validate_record_invalid_category():
    record = {"key": "a", "value": 1, "category": "bogus"}
    assert validate_record(record) is False


# --- db tests edge cases ---

def test_db_clear_multiple_records(clean_db):
    db.insert_record("k1", "v1", "metrics")
    db.insert_record("k2", "v2", "labels")
    db.clear_all()
    rows = db.get_all_unprocessed()
    assert rows == []


def test_db_mark_processed(clean_db):
    rid = db.insert_record("k", "v", "metrics")
    db.mark_processed(rid)
    unprocessed = db.get_all_unprocessed()
    assert len(unprocessed) == 0


# --- ingestor tests ---

def test_ingestor_load_csv():
    from target_pipeline.ingestor import load_csv
    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        f.write("k1,v1,metrics\n")
        f.write("k2,v2,labels\n")
        path = f.name
    try:
        rows = load_csv(path)
        assert len(rows) == 2
        assert rows[0]["key"] == "k1"
    finally:
        os.unlink(path)


def test_ingestor_validate_row():
    from target_pipeline.ingestor import validate_row
    assert validate_row({"key": "k", "value": "v", "category": "metrics"}) is True
    assert validate_row({"key": "k", "value": "", "category": "metrics"}) is False
    assert validate_row({"key": "k", "category": "metrics"}) is False


def test_ingestor_ingest_file(clean_db):
    from target_pipeline.ingestor import ingest_file
    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        f.write("k1,v1,metrics\n")
        f.write("k2,v2,labels\n")
        path = f.name
    try:
        ids = ingest_file(path)
        assert len(ids) == 2
        assert all(isinstance(i, int) for i in ids)
    finally:
        os.unlink(path)


# --- integration tests ---

def test_full_pipeline_flow(clean_db):
    """Integration test: ingest, transform, validate, export."""
    from target_pipeline.ingestor import ingest_file
    from target_pipeline.transformer import transform_batch
    from target_pipeline.validator import get_valid_records

    # Create a test CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        f.write("metric1,42,metrics\n")
        f.write("label1,hello,labels\n")
        path = f.name

    try:
        # Ingest
        ids = ingest_file(path)
        assert len(ids) == 2

        # Retrieve and transform
        records = db.get_records_by_ids(ids)
        transformed = transform_batch(records)
        assert len(transformed) == 2

        # Validate
        valid_records = get_valid_records(transformed)
        assert len(valid_records) == 2

    finally:
        os.unlink(path)


# --- transformer edge cases ---

def test_parse_value_nan():
    result = parse_value(float('nan'), "metrics")
    assert result == 0.0


def test_parse_value_inf():
    result = parse_value(float('inf'), "metrics")
    assert result == 1e9  # clamped


def test_parse_value_negative_inf():
    result = parse_value(float('-inf'), "metrics")
    assert result == -1e9  # clamped


def test_parse_value_mixed_numeric():
    result = parse_value("3.14", "mixed")
    assert isinstance(result, float)


def test_parse_value_mixed_text():
    result = parse_value("hello", "mixed")
    assert isinstance(result, str)


def test_transform_record_none():
    from target_pipeline.transformer import transform_record
    assert transform_record(None) is None


def test_transform_record_invalid_category():
    from target_pipeline.transformer import transform_record
    record = (1, "key", "value", "invalid_cat", 0)
    result = transform_record(record)
    assert result is not None
    assert result["category"] == "unknown"


def test_transform_batch_mixed():
    from target_pipeline.transformer import transform_batch
    records = [
        (1, "k1", "42", "metrics", 0),
        None,
        (2, "k2", "text", "labels", 0),
    ]
    result = [r for r in [transform_batch([r]) for r in records] if r]
    assert len(result) >= 2


# --- validator edge cases ---

def test_validate_batch_mixed():
    from target_pipeline.validator import validate_batch
    records = [
        {"key": "a", "value": 1, "category": "metrics"},
        {"key": "b", "value": "text", "category": "invalid"},
    ]
    result = validate_batch(records)
    assert len(result) == 2
    assert result[0][1] is True
    assert result[1][1] is False


def test_get_invalid_records():
    from target_pipeline.validator import get_invalid_records
    records = [
        {"key": "a", "value": 1, "category": "metrics"},
        {"key": "", "value": 1, "category": "metrics"},
    ]
    invalid = get_invalid_records(records)
    assert len(invalid) == 1


# --- comprehensive integration tests ---

def test_end_to_end_pipeline(clean_db):
    """End-to-end: ingest, transform, validate, export all formats."""
    from target_pipeline.ingestor import ingest_file
    from target_pipeline.transformer import transform_batch
    from target_pipeline.validator import get_valid_records
    from target_pipeline.exporter import export_json, export_csv, export_summary

    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        f.write("metric_a,100,metrics\n")
        f.write("metric_b,42,scores\n")
        f.write("label_x,hello,labels\n")
        f.write("label_y,world,descriptions\n")
        csv_path = f.name

    try:
        # Ingest CSV
        ids = ingest_file(csv_path)
        assert len(ids) == 4

        # Transform records
        raw_records = db.get_records_by_ids(ids)
        transformed = transform_batch(raw_records)
        assert len(transformed) == 4

        # Validate
        valid = get_valid_records(transformed)
        assert len(valid) == 4

        # Export to all formats
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "out.json")
            csv_export_path = os.path.join(tmpdir, "out.csv")
            summary_path = os.path.join(tmpdir, "summary.json")

            json_count = export_json(valid, json_path)
            csv_count = export_csv(valid, csv_export_path)
            summary = export_summary(valid, summary_path)

            assert json_count == 4
            assert csv_count == 4
            assert summary["total_records"] == 4
            assert os.path.exists(json_path)
            assert os.path.exists(csv_export_path)
            assert os.path.exists(summary_path)

    finally:
        os.unlink(csv_path)


def test_pipeline_with_invalid_records(clean_db):
    """Test handling of invalid records in pipeline."""
    from target_pipeline.ingestor import ingest_file
    from target_pipeline.transformer import transform_batch
    from target_pipeline.validator import validate_batch, get_valid_records

    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        f.write("k1,v1,metrics\n")
        f.write("k2,v2,invalid_cat\n")
        csv_path = f.name

    try:
        ids = ingest_file(csv_path)
        raw_records = db.get_records_by_ids(ids)
        transformed = transform_batch(raw_records)

        # Validate batch
        validation_results = validate_batch(transformed)
        valid_count = sum(1 for _, is_valid in validation_results if is_valid)

        assert valid_count >= 1  # At least first record is valid

    finally:
        os.unlink(csv_path)


def test_large_dataset_pipeline(clean_db):
    """Test pipeline performance with larger dataset."""
    from target_pipeline.ingestor import ingest_file
    from target_pipeline.transformer import transform_batch

    # Create CSV with many records
    with tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False) as f:
        f.write("key,value,category\n")
        for i in range(20):
            f.write(f"metric_{i},{i*10},metrics\n")
        csv_path = f.name

    try:
        ids = ingest_file(csv_path)
        assert len(ids) == 20

        raw_records = db.get_records_by_ids_optimized(ids)
        assert len(raw_records) == 20

        transformed = transform_batch(raw_records)
        assert len(transformed) == 20

    finally:
        os.unlink(csv_path)


def test_export_with_various_types(clean_db):
    """Test exporting records with various data types."""
    from target_pipeline.exporter import export_json, export_csv

    records = [
        {"key": "int_val", "value": 42, "category": "metrics", "tags": ["numeric"]},
        {"key": "float_val", "value": 3.14, "category": "scores", "tags": ["numeric", "float"]},
        {"key": "str_val", "value": "hello", "category": "labels", "tags": ["text"]},
        {"key": "none_val", "value": None, "category": "mixed", "tags": []},
        {"key": "list_val", "value": [1, 2, 3], "category": "mixed", "tags": []},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "export.json")
        csv_path = os.path.join(tmpdir, "export.csv")

        json_count = export_json(records, json_path)
        csv_count = export_csv(records, csv_path)

        assert json_count == 5
        assert csv_count == 5

        # Verify JSON is valid
        with open(json_path) as f:
            data = json.load(f)
            assert len(data) == 5

        # Verify CSV has headers and rows
        with open(csv_path) as f:
            lines = f.readlines()
            assert len(lines) >= 5  # header + 5 data rows


# --- final edge cases and critical paths ---

def test_validate_numeric_none_value():
    assert validate_value(None, "metrics") is False
    assert validate_value(None, "labels") is True


def test_normalize_key_unicode():
    result = normalize_key("key_with_émojis_😀")
    assert isinstance(result, str)
    assert result != ""


def test_parse_value_whitespace_only():
    result = parse_value("   ", "labels")
    assert result == ""


def test_transform_record_with_tags():
    from target_pipeline.transformer import transform_record
    record = (42, "my_key", "1000", "metrics", 1)
    result = transform_record(record)
    assert "numeric" in result["tags"]
    assert "integer" in result["tags"]


def test_transform_record_long_text():
    from target_pipeline.transformer import transform_record
    long_text = "a" * 150
    record = (42, "key", long_text, "labels", 0)
    result = transform_record(record)
    assert "long-text" in result["tags"]


def test_ingestor_batch_with_empty_list(clean_db):
    from target_pipeline.ingestor import ingest_batch
    ids = ingest_batch([])
    assert ids == []


def test_db_audit_logging(clean_db):
    rid = db.insert_record("test_key", "test_val", "metrics")
    db.log_audit(rid, "created", "2025-03-28T00:00:00")
    db.log_audit(rid, "modified", "2025-03-28T00:01:00")
    # Verify no errors on multiple audits
    assert rid > 0


def test_validator_all_categories():
    """Test validation for all valid categories."""
    valid_cats = ["metrics", "scores", "counts", "measurements",
                  "labels", "descriptions", "tags", "notes", "mixed", "unknown"]
    for cat in valid_cats:
        record = {"key": "test", "value": "val", "category": cat}
        assert validate_record(record) is True


def test_exporter_summary_numeric_stats(clean_db):
    from target_pipeline.exporter import export_summary

    records = [
        {"key": "m1", "value": 10, "category": "metrics"},
        {"key": "m2", "value": 20, "category": "metrics"},
        {"key": "m3", "value": 30, "category": "metrics"},
        {"key": "l1", "value": "text", "category": "labels"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "summary.json")
        summary = export_summary(records, path)

        assert summary["total_records"] == 4
        assert summary["numeric_stats"]["count"] == 3
        assert summary["numeric_stats"]["min"] == 10
        assert summary["numeric_stats"]["max"] == 30
        assert summary["numeric_stats"]["avg"] == 20.0
        assert summary["category_breakdown"]["metrics"] == 3
        assert summary["category_breakdown"]["labels"] == 1
