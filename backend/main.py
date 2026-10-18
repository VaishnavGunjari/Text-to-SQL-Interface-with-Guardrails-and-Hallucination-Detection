"""FastAPI application entry point."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logger import setup_logging, get_logger
from config import get_settings
from database.connection import check_connection
from database.schema_inspector import get_schema
from api.routes import query, schema, history

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


API_DESCRIPTION = """
## Text-to-SQL AI Engine with Guardrails & Hallucination Detection

Production-ready service translating natural language inquiries into secure, validated SQL queries.

### 🛡️ Safety & Guardrail Architecture
- **AST SQL Guardrails**: Blocks DDL/DML mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`), enforces table whitelists, and injects default limits.
- **Hallucination Detection**: Verifies table and column references against the live schema and performs LLM back-translation to measure semantic query alignment.
- **Result Sanity Checks**: Validates result boundaries, unexpected empty sets, and extreme anomalies.
- **Multi-Query Validation**: Runs parallel independent query formulations to confirm consensus across alternative SQL patterns.
- **Transparent Confidence Scoring**: 100-point weighted score explaining exact criteria behind confidence ratings.

### 📚 Domain & Entities
Pre-configured for SaaS business analytics:
- `organizations`: Customer companies, plans, employee counts, churn dates.
- `users`: User accounts, organization assignments, roles, activity states.
- `subscriptions`: MRR, billing intervals, statuses, plan tiers.
- `invoices`: Amounts, payment statuses, due dates, paid timestamps.
- `events`: Product telemetry, feature usage, and user actions.
- `features`: Feature catalog and required subscription tiers.
- `feature_usage`: Volume tracking of feature consumption.
"""

tags_metadata = [
    {
        "name": "Query",
        "description": "Natural language query translation, multi-stage guardrail validation, execution, and human feedback collection.",
    },
    {
        "name": "Schema",
        "description": "Database schema introspection, table metadata, entity relationships, and cache invalidation.",
    },
    {
        "name": "History",
        "description": "Historical query audit log, confidence scores, row counts, and human feedback state.",
    },
    {
        "name": "System",
        "description": "Diagnostic health checks, database ping, and environment status.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Text-to-SQL AI service...")
    try:
        get_schema()
        logger.info("Database schema pre-warmed successfully")
    except Exception as e:
        logger.warning("Schema pre-warming failed", error=str(e))
    yield
    logger.info("Shutting down Text-to-SQL AI service...")


app = FastAPI(
    title="Text-to-SQL AI",
    summary="Intelligent, secure Natural Language to SQL interface with multi-stage verification.",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(query.router, prefix="/v1", tags=["Query"])
app.include_router(schema.router, prefix="/v1", tags=["Schema"])
app.include_router(history.router, prefix="/v1", tags=["History"])


@app.get("/v1/health", tags=["System"], summary="Health & Connectivity Status")
async def health():
    """Verify service uptime, PostgreSQL connectivity, and active model."""
    db_ok = check_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "model": settings.llm_model,
        "env": settings.app_env,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", error=str(exc), path=str(request.url))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
