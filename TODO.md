# TODO: MariaDB AI Optimizer Project Implementation

## Root Files
- [ ] render.yaml: Configure for Render deployment (services for API and web).
- [ ] README.md: Detailed setup, usage, agent descriptions, screenshots placeholders.
- [ ] .zencoder/rules/repo.md: Basic repo rules (e.g., commit message format).

## API Backend
- [ ] api/pyproject.toml: Define project with dependencies (fastapi==0.104.1, uvicorn==0.24.0, sqlalchemy==2.0.23, pymysql==1.1.0, pydantic-settings==2.1.0).
- [ ] api/Dockerfile: Build FastAPI app with Python 3.11, copy code, expose 8000.
- [ ] api/.env.example: Template for DB_HOST, DB_PORT=3306, DB_USER, DB_PASS, DB_NAME.
- [ ] api/app/settings.py: Load env vars for DB connection.
- [ ] api/app/db.py: Async SQLAlchemy engine for MariaDB.
- [x] api/app/utils/explain.py: Function to execute EXPLAIN on SQL query.
- [x] api/app/utils/introspection.py: Functions for SHOW TABLES, DESCRIBE, etc.
- [x] api/app/utils/cost_stats.py: Query PERFORMANCE_SCHEMA for execution times.
- [x] api/app/agents/query_optimizer.py: Analyze SQL (simple rule-based + EXPLAIN), suggest rewrites/indexes.
- [x] api/app/agents/schema_normalizer.py: Fetch schema, suggest normalization/denorm, indexes.
- [x] api/app/agents/cost_saver.py: Review queries for high-cost patterns, suggest optimizations.
- [x] api/app/agents/data_validation.py: Compare table stats (counts, sums) with expected.
- [x] api/app/main.py: FastAPI app with /health, /optimize-query (POST SQL), /normalize-schema (POST table names), etc.



## Followup Steps
- [ ] Install deps: API (poetry install or pip).
- [ ] Run: API (uvicorn app.main:app --reload).
- [ ] Test: Connect to sample MariaDB DB, use Swagger UI at /docs to interact.
- [ ] Deploy: Use render.yaml for Render.com.
