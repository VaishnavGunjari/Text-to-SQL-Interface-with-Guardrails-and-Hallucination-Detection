"""Schema endpoint."""
from fastapi import APIRouter
from database.schema_inspector import schema_to_dict, get_schema

router = APIRouter()


@router.get("/schema")
async def get_schema_endpoint():
    """Return the full database schema."""
    return schema_to_dict()


@router.post("/schema/refresh")
async def refresh_schema():
    """Force a schema cache refresh."""
    schema = get_schema(refresh=True)
    return {"status": "refreshed", "tables": len(schema.tables)}
