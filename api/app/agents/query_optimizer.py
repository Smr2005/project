from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.explain import explain_query
from ..utils.introspection import get_schema_context
from ..utils.claude_client import call_claude_json


class QueryOptimizer:
    """
    Agent for optimizing MariaDB SQL queries using Claude AI.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def optimize(self, query: str) -> Dict[str, Any]:
        """
        Optimize a given SQL query using Claude AI.

        Args:
            query: The SQL query string.

        Returns:
            Dict with AI-generated optimizations, recommendations, and analysis.
        """
        result = {
            "original_query": query,
            "optimized_query": query,
            "recommendations": [],
            "warnings": [],
            "estimated_impact": "low",
            "analysis": {},
            "success": True
        }

        try:
            # Get EXPLAIN plan
            plan = await explain_query(self.session, query)
            result["analysis"]["explain_plan"] = plan

            # Get schema context
            schema = await get_schema_context(self.session, query)
            result["analysis"]["schema"] = schema

            # Claude prompt for MariaDB-specific optimization
            prompt = f"""
You are a MariaDB query optimization expert. Analyze the following query for performance issues, focusing on InnoDB engine, BTREE indexes, buffer pool usage, and EXPLAIN plan.

Query: {query}

Schema: {str(schema)}

EXPLAIN Plan: {str(plan)}

Provide MariaDB-specific advice: suggest indexes (e.g., CREATE INDEX on join/WHERE columns), rewrites to avoid full scans/filesort/temp tables, use STRAIGHT_JOIN if needed, or buffer pool tuning.

Return STRICT JSON:
{{
  "optimized_query": "rewritten SQL or original",
  "recommendations": ["Index on column X for WHERE", "Add LIMIT to reduce rows", "InnoDB buffer pool size increase"],
  "warnings": ["Full table scan detected", "High cardinality join"],
  "estimated_impact": "low|medium|high",
  "mariaDB_tips": ["Specific InnoDB advice"]
}}
"""
            ai_response = await call_claude_json(prompt, max_tokens=1500)
            if "error" not in ai_response:
                result["optimized_query"] = ai_response.get("optimized_query", query)
                result["recommendations"] = ai_response.get("recommendations", [])
                result["warnings"] = ai_response.get("warnings", [])
                result["estimated_impact"] = ai_response.get("estimated_impact", "low")
                result["analysis"]["ai_mariaDB_tips"] = ai_response.get("mariaDB_tips", [])
            else:
                result["success"] = False
                result["error"] = ai_response["error"]

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result
