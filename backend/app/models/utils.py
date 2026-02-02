"""
PartnerCalc OS - Model Utilities
Cross-database compatible types
"""
from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB
from sqlalchemy.types import TypeDecorator
import json

from app.config import settings


def get_json_type():
    """Return JSONB for PostgreSQL, JSON for SQLite"""
    if settings.use_sqlite:
        return JSON
    return PG_JSONB


def get_array_type(item_type=Text):
    """Return ARRAY for PostgreSQL, JSON for SQLite"""
    if settings.use_sqlite:
        return JSON  # Store arrays as JSON in SQLite
    return PG_ARRAY(item_type)


# Convenient aliases
JSONB = get_json_type()
ArrayType = get_array_type
