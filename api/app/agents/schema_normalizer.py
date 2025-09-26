from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.introspection import describe_table, get_indexes, get_foreign_keys, get_tables
from ..utils.claude_client import call_claude_json


class SchemaNormalizer:
    """
    Agent for reviewing and suggesting schema normalization/denormalization improvements using Claude AI.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def normalize(self, table_names: List[str]) -> Dict[str, Any]:
        """
        Analyze tables for normalization/denormalization using Claude AI.

        Args:
            table_names: List of table names to analyze.

        Returns:
            Dict with AI-generated schema suggestions.
        """
        result = {
            "tables_analyzed": table_names,
            "recommended_indexes": [],
            "schema_changes": [],
            "warnings": [],
            "overall_advice": [],
            "success": True
        }

        try:
            # Get schema for all tables
            schema_info = {}
            for table in table_names:
                columns = await describe_table(self.session, table)
                indexes = await get_indexes(self.session, table)
                fks = await get_foreign_keys(self.session, table)
                schema_info[table] = {
                    "columns": columns,
                    "indexes": indexes,
                    "foreign_keys": fks
                }

            # Claude prompt for MariaDB schema advice
            schema_str = str(schema_info)
            prompt = f"""
You are a MariaDB schema expert. Analyze the schema for normalization/denormalization opportunities, focusing on InnoDB: suggest BTREE indexes, partitioning for large tables, column type optimizations (VARCHAR vs TEXT, DECIMAL precision), foreign key constraints.

Tables: {', '.join(table_names)}

Schema Details: {schema_str}

Provide MariaDB-specific recommendations: normalize to reduce redundancy or denormalize for read speed, add indexes on FKs/joins.

Return STRICT JSON:
{{
  "recommended_indexes": ["CREATE INDEX idx_name ON table(column)"],
  "schema_changes": ["ALTER TABLE table ADD COLUMN...", "ALTER TABLE table MODIFY COLUMN..."],
  "warnings": ["Over-normalized joins may slow queries", "Missing indexes on FKs"],
  "overall_advice": ["InnoDB row compression for storage savings"]
}}
"""
            ai_response = await call_claude_json(prompt, max_tokens=1200)
            if "error" not in ai_response:
                result["recommended_indexes"] = ai_response.get("recommended_indexes", [])
                result["schema_changes"] = ai_response.get("schema_changes", [])
                result["warnings"] = ai_response.get("warnings", [])
                result["overall_advice"] = ai_response.get("overall_advice", [])
                result["analysis"] = {"schema_info": schema_info}
            else:
                result["success"] = False
                result["error"] = ai_response["error"]

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result
