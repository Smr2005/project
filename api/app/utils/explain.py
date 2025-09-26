from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def explain_query(session: AsyncSession, query: str) -> dict:
    """
    Execute EXPLAIN on a given SQL query and return the plan as a dict.

    Args:
        session: Async SQLAlchemy session.
        query: The SQL query to explain.

    Returns:
        Dict containing EXPLAIN output or error.
    """
    try:
        explain_sql = f"EXPLAIN FORMAT=JSON {query}"
        result = await session.execute(text(explain_sql))
        row = result.fetchone()
        if row:
            # Assuming JSON format, parse if needed
            return {"plan": row[0], "success": True}
        return {"error": "No EXPLAIN output", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


async def analyze_plan(plan: dict) -> list[str]:
    """
    Analyze EXPLAIN plan for common issues.

    Args:
        plan: EXPLAIN output dict.

    Returns:
        List of suggestions.
    """
    suggestions = []
    if "error" in plan:
        suggestions.append("Query execution failed; check syntax.")
        return suggestions

    # Simple rule-based analysis (expand with more logic)
    plan_str = str(plan.get("plan", "")).lower()
    if "full table scan" in plan_str or "all" in plan_str:
        suggestions.append("Consider adding indexes on WHERE/join columns to avoid full scans.")
    if "filesort" in plan_str:
        suggestions.append("Query uses filesort; optimize ORDER BY with indexes.")
    if "temporary" in plan_str:
        suggestions.append("Query creates temp table; consider rewriting joins or subqueries.")

    return suggestions
