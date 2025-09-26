# agents/schema_advisor.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)
DANGEROUS = ["delete", "update", "drop", "truncate", "alter"]

def _is_safe(sql: str):
    return not any(k in sql.lower() for k in DANGEROUS)

def advise_schema(sql: str, schema: dict):
    base = {"agent": "schema_advisor", "status": None, "query": sql, "safe_query": None, "details": {}}
    if not _is_safe(sql):
        prompt = f"""
The query below is unsafe:
{sql}

Return JSON with a safe SELECT preview and explanation:
{{ "safe_preview": "SELECT ...", "explanation": "..." }}
"""
        resp = call_claude_json(prompt)
        if "error" in resp:
            return {**base, "status": "error", "details": {"error": resp.get("error")}}
        return {**base, "status": "unsafe", "safe_query": resp.get("safe_preview"), "details": {"reasoning": resp.get("explanation")}}

    prompt = f"""
You are a Schema Advisor for MariaDB/MySQL.

INPUT:
SQL:
{sql}

SCHEMA:
{json.dumps(schema, indent=2, default=str)}

Task:
Suggest schema improvements (indexes, partitioning, column types) to make this query faster.
Return JSON ONLY:
{{
  "recommended_indexes": ["CREATE INDEX ..."],
  "schema_changes": ["ALTER TABLE ...", "..."],
  "warnings": ["..."]
}}
"""
    resp = call_claude_json(prompt)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "recommendations": resp.get("recommended_indexes", []),
        "schema_changes": resp.get("schema_changes", []),
        "warnings": resp.get("warnings", [])
    }
    return {**base, "status": "success", "details": details}
