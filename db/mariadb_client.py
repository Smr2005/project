import aiomysql
import re

class MariaDBClient:
    def __init__(self, host, user, password, database, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.pool = None

    async def connect(self):
        if self.pool is None:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.database,
                port=self.port,
                autocommit=True,
            )

    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def explain(self, query: str):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f"EXPLAIN {query}")
                return await cur.fetchall()

    async def fetch_sample_rows(self, query: str, limit: int = 5):
        """Fetch sample rows from query safely (works with aggregates too)."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                try:
                    q = query.rstrip(";")

                    # If query already has LIMIT, run as is
                    if re.search(r"\blimit\b", q, re.IGNORECASE):
                        safe_query = q
                    else:
                        safe_query = f"SELECT * FROM ({q}) AS subq LIMIT {limit}"

                    await cur.execute(safe_query)
                    rows = await cur.fetchall()

                    if not rows:
                        return {"rows": [], "message": "Query returned no rows"}

                    # Clean up aggregate column names
                    cleaned_rows = []
                    for row in rows:
                        new_row = {}
                        for k, v in row.items():
                            clean_key = (
                                k.replace("COUNT(*)", "total_count")
                                .replace("SUM(", "sum_")
                                .replace(")", "")
                                .replace("AVG(", "avg_")
                                .replace("MAX(", "max_")
                                .replace("MIN(", "min_")
                            )
                            # fallback: lowercase & replace spaces
                            clean_key = re.sub(r"\W+", "_", clean_key).strip("_").lower()
                            new_row[clean_key] = v
                        cleaned_rows.append(new_row)

                    return {
                        "rows": cleaned_rows,
                        "message": f"Showing up to {limit} rows from actual query"
                    }

                except Exception as e:
                    return {"error": f"Sample row fetch failed: {str(e)}"}

    async def get_schema_context(self, query: str):
        """Extract table names from query and return schema details."""
        tables = self._extract_tables(query)
        schema = {}
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                for tbl in tables:
                    try:
                        await cur.execute(f"DESCRIBE {tbl}")
                        schema[tbl] = await cur.fetchall()
                    except Exception as e:
                        schema[tbl] = {"error": str(e)}
        return schema

    async def get_full_schema(self):
        """Return full database schema overview via information_schema."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_TYPE
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """
                )
                rows = await cur.fetchall()
        tables = {}
        for r in rows:
            t = r["TABLE_NAME"]
            tables.setdefault(t, []).append(r)
        return tables

    def _extract_tables(self, query: str):
        """More tolerant regex-based table extractor: handles backticks and schema-qualified."""
        # matches from/join followed by optional schema and backticks
        matches = re.findall(r"(?:from|join)\s+(`?[\w\.]+`?)", query, re.IGNORECASE)
        # Strip backticks
        cleaned = [m.replace("`", "") for m in matches]
        # Only table part if schema qualified
        return [c.split(".")[-1] for c in cleaned if c]
