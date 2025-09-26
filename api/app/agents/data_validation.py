from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.introspection import get_tables
from ..utils.claude_client import call_claude_json


class DataValidator:
    """
    Agent for validating data integrity between MariaDB tables and sources using Claude AI.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate(self, table_name: str, source_query: str = None, expected_count: int = None) -> Dict[str, Any]:
        """
        Validate data in a table against source or expectations using Claude AI.

        Args:
            table_name: Table to validate.
            source_query: Optional SQL query for source data (e.g., external).
            expected_count: Expected row count.

        Returns:
            Dict with AI-generated validation results.
        """
        result = {
            "table_name": table_name,
            "issues": [],
            "confidence": "medium",
            "reasoning": "",
            "success": True
        }

        try:
            # Row count validation
            if expected_count is not None:
                actual_count = await self._get_row_count(table_name)
                if actual_count != expected_count:
                    result["issues"].append({
                        "type": "row_count_mismatch",
                        "expected": expected_count,
                        "actual": actual_count
                    })

            # Source comparison (if provided)
            if source_query:
                source_count = await self._execute_count_query(source_query)
                table_count = await self._get_row_count(table_name)
                if source_count != table_count:
                    result["issues"].append({
                        "type": "source_mismatch",
                        "source_count": source_count,
                        "table_count": table_count
                    })

            # Integrity checks
            anomalies = await self._check_integrity(table_name)
            result["issues"].extend(anomalies)

            # Sample data
            samples = await self._sample_data(table_name)
            samples_str = str(samples)

            # Claude prompt for MariaDB data validation
            issues_str = str(result["issues"])
            prompt = f"""
You are a MariaDB data validation expert. Analyze the table data for integrity issues, focusing on MariaDB data types (DECIMAL, DATE, VARCHAR), referential integrity, duplicates, null anomalies.

Table: {table_name}

Sample Data: {samples_str}

Detected Issues: {issues_str}

Provide MariaDB-specific validation: check for DECIMAL precision issues, DATE format consistency, VARCHAR length overflows, FK violations.

Return STRICT JSON:
{{
  "issues": ["DECIMAL values exceed precision", "Duplicate rows on unique columns", "Null FKs violating constraints"],
  "confidence": "high|medium|low",
  "reasoning": "Explanation of findings and MariaDB-specific advice"
}}
"""
            ai_response = await call_claude_json(prompt, max_tokens=800)
            if "error" not in ai_response:
                result["issues"] = ai_response.get("issues", result["issues"])
                result["confidence"] = ai_response.get("confidence", "medium")
                result["reasoning"] = ai_response.get("reasoning", "")
                result["validations"] = {"samples": samples}
            else:
                result["success"] = False
                result["error"] = ai_response["error"]

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    async def _get_row_count(self, table_name: str) -> int:
        """
        Get row count for a table.

        Args:
            table_name: Table name.

        Returns:
            Row count.
        """
        result = await self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()

    async def _execute_count_query(self, query: str) -> int:
        """
        Execute a count query.

        Args:
            query: SQL query.

        Returns:
            Count result.
        """
        result = await self.session.execute(text(query))
        return result.scalar()

    async def _check_integrity(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Check for integrity issues like null FKs, duplicates.

        Args:
            table_name: Table name.

        Returns:
            List of anomalies.
        """
        anomalies = []

        # Check for nulls in non-nullable columns (simplified)
        # In real impl, use DESCRIBE to find NOT NULL columns
        null_check = await self.session.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE id IS NULL"))
        null_count = null_check.scalar()
        if null_count > 0:
            anomalies.append({"type": "null_primary_key", "count": null_count})

        # Check for duplicates (assuming id is PK)
        dup_check = await self.session.execute(text(f"""
            SELECT id, COUNT(*) as cnt FROM {table_name} GROUP BY id HAVING cnt > 1 LIMIT 5
        """))
        dups = dup_check.fetchall()
        if dups:
            anomalies.append({"type": "duplicate_ids", "samples": [row[0] for row in dups]})

        return anomalies

    async def _sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Sample rows from the table.

        Args:
            table_name: Table name.
            limit: Number of samples.

        Returns:
            List of sample rows.
        """
        result = await self.session.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
        samples = [dict(row) for row in result.fetchall()]
        return samples
