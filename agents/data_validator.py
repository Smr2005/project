# agents/data_validator.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)

def validate_query(sql: str, sample_rows: dict):
    base = {"agent": "data_validator", "status": None, "query": sql, "details": {}}
    prompt = f"""
You are a Data Validator.

SQL:
{sql}

SAMPLE_ROWS:
{json.dumps(sample_rows, indent=2, default=str)}

Inspect sample rows for data quality issues (missing values, wrong datatypes, suspicious outliers) and return JSON ONLY:
{{
  "issues": ["..."],
  "confidence": "high|medium|low",
  "reasoning": "..."
}}
"""
    resp = call_claude_json(prompt, max_tokens=600)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "issues": resp.get("issues", []),
        "confidence": resp.get("confidence"),
        "reasoning": resp.get("reasoning")
    }
    return {**base, "status": "success", "details": details}
