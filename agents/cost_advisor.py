# agents/cost_advisor.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)

def estimate_cost(sql: str, explain):
    base = {"agent": "cost_advisor", "status": None, "query": sql, "details": {}}
    prompt = f"""
You are a Cost Advisor for MariaDB.

SQL:
{sql}

EXPLAIN:
{json.dumps(explain, indent=2, default=str)}

Estimate relative cost/IO/runtime and give concrete tips to reduce cost.
Return JSON ONLY:
{{
  "estimated_cost": "low|medium|high or numeric",
  "cost_saving_tips": ["..."],
  "warnings": ["..."]
}}
"""
    resp = call_claude_json(prompt, max_tokens=800)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "estimated_cost": resp.get("estimated_cost"),
        "cost_saving_tips": resp.get("cost_saving_tips", []),
        "warnings": resp.get("warnings", [])
    }
    return {**base, "status": "success", "details": details}
