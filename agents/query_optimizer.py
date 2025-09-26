# agents/query_optimizer.py
import json
import logging
from typing import Dict, Any
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)

def optimize_query(sql: str,
                   schema: Dict[str, Any],
                   explain: Dict[str, Any],
                   sample_rows: Dict[str, Any],
                   target_engine: str = "mariadb") -> Dict[str, Any]:
    """
    Claude-powered Query Optimizer (MariaDB-focused)
    - Calls Claude with schema + EXPLAIN + SQL
    - Expects structured JSON with optimized query, recommendations, warnings, impact, etc.
    """

    prompt = f"""
You are a world-class SQL performance tuning agent specialized in MariaDB/MySQL.

Your role: optimize SQL queries for performance and cost.

### Input
Original Query:
{sql}

Schema Context:
{json.dumps(schema, indent=2, default=str)}

Explain Plan:
{json.dumps(explain, indent=2, default=str)}

Sample Rows:
{json.dumps(sample_rows, indent=2, default=str)}

### Rules (MariaDB)
- Rewrite query only if the execution plan will improve (not just formatting).
- Detect and avoid: full table scans, cross joins, filesort/temp tables, unnecessary GROUP BY/ORDER BY.
- Recommend B-Tree indexes and composite indexes where appropriate.
- Recommend avoiding SELECT *; prefer explicit columns.
- Consider using temporary tables or materialized strategies for reuse-heavy subqueries.
- Estimate qualitative impact (low/medium/high) and explain why.
- Return STRICT JSON ONLY with the following keys:
  {{
    "optimized_query": "...",
    "why_faster": "...",
    "recommendations": ["...", "..."],
    "warnings": ["..."],
    "estimated_impact": "low|medium|high",
    "engine_advice": ["MariaDB specific advice ..."],
    "materialization_advice": ["..."]
  }}
    """

    try:
        resp = call_claude_json(prompt, max_tokens=1000)
        if "error" in resp:
            return {
                "status": "error",
                "details": {"error": resp.get("error"), "optimized_query": sql}
            }
        return {"status": "success", "details": resp}
    except Exception as e:
        logger.exception("Claude query optimization failed")
        return {
            "status": "error",
            "details": {"error": str(e), "optimized_query": sql}
        }
