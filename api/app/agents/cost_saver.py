from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.cost_stats import detect_expensive_queries, get_table_stats
from ..utils.claude_client import call_claude_json


class CostSaver:
    """
    Agent for identifying and reducing query/storage costs in MariaDB using Claude AI.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_costs(self, queries: List[str] = None) -> Dict[str, Any]:
        """
        Analyze queries or database for cost-saving opportunities using Claude AI.

        Args:
            queries: Optional list of queries to analyze; if None, scan expensive ones.

        Returns:
            Dict with AI-generated cost analysis and suggestions.
        """
        result = {
            "expensive_queries": [],
            "table_costs": [],
            "cost_saving_tips": [],
            "warnings": [],
            "estimated_savings": {},
            "success": True
        }

        try:
            # Detect expensive queries
            if queries:
                for q in queries:
                    stats = await get_query_stats(self.session, q)
                    if stats.get("execution_time", 0) > 1.0:  # Threshold
                        result["expensive_queries"].append({"query": q, "stats": stats})
            else:
                expensive = await detect_expensive_queries(self.session)
                result["expensive_queries"] = expensive

            # Analyze tables for storage costs
            tables = await self._get_large_tables()
            for table in tables:
                stats = await get_table_stats(self.session, table)
                result["table_costs"].append(stats)

            # Prepare data for Claude
            queries_str = "\n".join([eq["query"] for eq in result["expensive_queries"]]) if result["expensive_queries"] else "No expensive queries provided"
            tables_str = str(result["table_costs"])

            # Claude prompt for MariaDB cost advice
            prompt = f"""
You are a MariaDB cost optimization expert. Analyze the expensive queries and table stats for cost-saving opportunities, focusing on InnoDB buffer pool, query cache, compression, archiving, and partitioning.

Expensive Queries:
{queries_str}

Table Stats:
{tables_str}

Provide MariaDB-specific tips: reduce IO with indexes, tune buffer pool size, use compressed row format, suggest materialized views or data unloading.

Return STRICT JSON:
{{
  "cost_saving_tips": ["Increase buffer pool for frequent tables", "Partition large tables by date", "Enable query cache for reads"],
  "warnings": ["High IO on full scans", "Large temp tables indicate poor joins"],
  "estimated_savings": {{"storage_mb": 100, "query_time_reduction_percent": 30, "overall_cost_reduction_percent": 20}}
}}
"""
            ai_response = await call_claude_json(prompt, max_tokens=1000)
            if "error" not in ai_response:
                result["cost_saving_tips"] = ai_response.get("cost_saving_tips", [])
                result["warnings"] = ai_response.get("warnings", [])
                result["estimated_savings"] = ai_response.get("estimated_savings", {})
            else:
                result["success"] = False
                result["error"] = ai_response["error"]

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    async def _get_large_tables(self) -> List[str]:
        """
        Get list of large tables (by row count or size).

        Returns:
            List of table names.
        """
        # Placeholder: In real impl, query INFORMATION_SCHEMA
        # For now, return sample
        return ["users", "orders", "logs"]  # Replace with actual query
