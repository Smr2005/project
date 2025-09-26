from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from .db import get_db
from .agents.query_optimizer import QueryOptimizer
from .agents.schema_normalizer import SchemaNormalizer
from .agents.cost_saver import CostSaver
from .agents.data_validation import DataValidator

app = FastAPI(
    title="MariaDB AI Optimizer API",
    description="AI-powered sub-agents for MariaDB query and schema optimization",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-frontend-domain.com"],  # Update for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    query: str

class SchemaRequest(BaseModel):
    table_names: List[str]

class ValidationRequest(BaseModel):
    table_name: str
    source_query: Optional[str] = None
    expected_count: Optional[int] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MariaDB AI Optimizer"}

@app.post("/optimize-query")
async def optimize_query(request: QueryRequest, session: AsyncSession = Depends(get_db)):
    """
    Optimize a SQL query using the Query Optimizer agent.
    """
    try:
        optimizer = QueryOptimizer(session)
        result = await optimizer.optimize(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/normalize-schema")
async def normalize_schema(request: SchemaRequest, session: AsyncSession = Depends(get_db)):
    """
    Analyze and suggest schema improvements.
    """
    try:
        normalizer = SchemaNormalizer(session)
        result = await normalizer.normalize(request.table_names)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-costs")
async def save_costs(queries: Optional[List[str]] = None, session: AsyncSession = Depends(get_db)):
    """
    Identify cost-saving opportunities.
    """
    try:
        saver = CostSaver(session)
        result = await saver.save_costs(queries)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate-data")
async def validate_data(request: ValidationRequest, session: AsyncSession = Depends(get_db)):
    """
    Validate data integrity.
    """
    try:
        validator = DataValidator(session)
        result = await validator.validate(
            request.table_name,
            request.source_query,
            request.expected_count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
