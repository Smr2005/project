from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import re
import logging
logger = logging.getLogger(__name__)

from utils.config import Config
from db.mariadb_client import MariaDBClient
from agents.query_optimizer import optimize_query
from agents.cost_advisor import estimate_cost
from agents.schema_advisor import advise_schema
from agents.data_validator import validate_query

app = FastAPI(title="MariaDB Query Optimizer (AI Agents)")

# CORS (open for dev; tighten for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    sql: str
    run_in_sandbox: bool = True

# DB client (currently single target; you could swap DB based on run_in_sandbox)
db_client = MariaDBClient(
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME,
    port=Config.DB_PORT,
)

@app.on_event("startup")
async def startup_event():
    await db_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db_client.disconnect()

# --- Safety: allow only SELECT/CTE queries ---
FORBIDDEN = ["insert", "update", "delete", "drop", "truncate", "alter", "create", "replace"]

def is_select_only(sql: str) -> bool:
    q = sql.strip().lower()
    if any(re.search(rf"\b{kw}\b", q) for kw in FORBIDDEN):
        return False
    return q.startswith("select") or q.startswith("with")

# -------- API endpoint --------
@app.post("/analyze")
async def analyze(request: QueryRequest):
    query = request.sql.strip()
    if not query:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")

    if not is_select_only(query):
        raise HTTPException(status_code=400, detail="Only SELECT/CTE queries are allowed.")

    try:
        schema_context = await db_client.get_schema_context(query)
        explain_plan = await db_client.explain(query)

        try:
            sample_rows = await db_client.fetch_sample_rows(query)
        except Exception as e:
            sample_rows = {"error": str(e)}

        # MariaDB-focused optimizer + sub-agents
        opt = optimize_query(query, schema_context, explain_plan, sample_rows, target_engine="mariadb")
        details = opt.get("details", {})

        # Additional assistants
        try:
            cost = estimate_cost(query, explain_plan)
        except Exception as e:
            cost = {"status": "error", "details": {"error": str(e)}}
        try:
            schema_adv = advise_schema(query, schema_context)
        except Exception as e:
            schema_adv = {"status": "error", "details": {"error": str(e)}}
        try:
            data_val = validate_query(query, sample_rows)
        except Exception as e:
            data_val = {"status": "error", "details": {"error": str(e)}}

        # Surface sub-agent outputs under ai_details for UI
        details["ai_details"] = {
            "cost_advisor": cost,
            "schema_advisor": schema_adv,
            "data_validator": data_val,
        }

        return {
            "original_query": query,
            "schema_context": schema_context,
            "explain_plan": explain_plan,
            "sample_rows": sample_rows,
            "analysis": details,
            "optimized_query": details.get("optimized_query", query),
            "database_used": Config.DB_NAME,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Schema overview endpoint used by frontend button ---
@app.post("/analyze-schema")
async def analyze_schema():
    try:
        full_schema = await db_client.get_full_schema()
        return {"database": Config.DB_NAME, "tables": full_schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join("static", "index.html"))
