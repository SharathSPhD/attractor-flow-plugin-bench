"""
Minimal happy-path tests for target_pipeline_original.
15 tests total, happy-path only, targeting ~42% source coverage.
"""

import os
import json
import tempfile

import pytest
from target_pipeline_original.transformer import parse_value, normalize_key
from target_pipeline_original.validator import (
    validate_key, validate_category, validate_value,
)
from target_pipeline_original.exporter import export_json, export_csv
from target_pipeline_original import db


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
