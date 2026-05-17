"""Safe JSON parsing for DB JSONB columns and LLM responses."""
import json
from typing import Any, TypeVar

T = TypeVar("T")


def parse_db_json(value: Any, default: T | None = None) -> Any:
    """Parse a DB JSON/JSONB field that may already be a dict or list (psycopg2)."""
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return default if default is not None else {}


def parse_llm_json(content: Any) -> dict:
    """Parse LLM message content that should be a JSON object."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str) and content.strip():
        return json.loads(content)
    raise ValueError("LLM returned empty or non-JSON content")
