from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from ..settings import settings


async def get_query_stats(session: AsyncSession, query: str) -> Dict[str, Any]:
    """
    Execute a query and gather performance stats using PERFORMANCE_SCHEMA (if enabled).

    Args:
        session: Async SQLAlchemy session.
        query: The SQL query to execute and measure.

    Returns:
        Dict with execution time, rows affected, etc.
    """
    if not settings.performance_schema_enabled:
        # Fallback: Simple execution without detailed stats
        try:
            import time
            start = time.time()
            result = await session.execute(text(query))
            rows = result.fetchall()
            end = time.time()
            return {
                "execution_time": end - start,
                "rows_affected": len(rows),
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    # Advanced: Use PERFORMANCE_SCHEMA (requires setup)
    try:
        # Enable events_statements_current
        await session.execute(text("SET profiling = 1"))
        await session.execute(text(query))
        # Get profile
        profile_result = await session.execute(text("SHOW PROFILE"))
        profiles = profile_result.fetchall()
        if profiles:
            # Parse profile (simplified)
            total_time = sum(float(row[1]) for row in profiles if row[1])
            return {
                "execution_time": total_time,
                "profile_steps": [{"operation": row[0], "duration": row[1]} for row in profiles],
                "success": True
            }
        return {"execution_time": 0, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


async def get_table_stats(session: AsyncSession, table_name: str) -> Dict[str, Any]:
    """
    Get statistics for a table (row count, size, etc.).

    Args:
        session: Async SQLAlchemy session.
        table_name: Name of the table.

    Returns:
        Dict with table stats.
    """
    try:
        # Row count
        count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        row_count = count_result.scalar()

        # Table size (approximate)
        size_result = await session.execute(text(f"""
            SELECT 
                ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
        """))
        size_mb = size_result.scalar() or 0

        return {
            "table_name": table_name,
            "row_count": row_count,
            "size_mb": size_mb,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}


async def detect_expensive_queries(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve top expensive queries from PERFORMANCE_SCHEMA (if available).

    Args:
        session: Async SQLAlchemy session.
        limit: Number of queries to return.

    Returns:
        List of dicts with query info.
    """
    if not settings.performance_schema_enabled:
        return [{"error": "PERFORMANCE_SCHEMA not enabled"}]

    try:
        query = text("""
            SELECT 
                DIGEST_TEXT AS query,
                AVG_TIMER_WAIT / 1000000000 AS avg_time_sec,
                COUNT_STAR AS exec_count
            FROM performance_schema.events_statements_summary_by_digest
            WHERE DIGEST_TEXT IS NOT NULL
            ORDER BY AVG_TIMER_WAIT DESC
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        queries = []
        for row in result.fetchall():
            queries.append({
                "query": row[0],
                "avg_time_sec": row[1],
                "exec_count": row[2]
            })
        return queries
    except Exception as e:
        return [{"error": str(e)}]
