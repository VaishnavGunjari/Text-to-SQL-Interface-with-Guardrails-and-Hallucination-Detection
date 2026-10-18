"""Schema introspection using SQLAlchemy reflection."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy import inspect, text
from database.connection import rw_engine
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool
    foreign_key: str | None = None
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    row_count: int = 0
    description: str = ""


@dataclass
class SchemaInfo:
    tables: list[TableInfo] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)


_schema_cache: SchemaInfo | None = None


def get_schema(refresh: bool = False) -> SchemaInfo:
    """Return cached schema or inspect the database."""
    global _schema_cache
    if _schema_cache is not None and not refresh:
        return _schema_cache
    _schema_cache = _inspect_schema()
    return _schema_cache


def _inspect_schema() -> SchemaInfo:
    logger.info("Inspecting database schema")
    inspector = inspect(rw_engine)
    table_names = inspector.get_table_names(schema="public")
    schema = SchemaInfo()

    for table_name in table_names:
        if table_name.startswith("_"):
            continue  # skip internal tables

        # Columns
        columns_raw = inspector.get_columns(table_name, schema="public")
        pk_cols = {c for c in inspector.get_pk_constraint(table_name, schema="public").get("constrained_columns", [])}
        fk_map = {}
        for fk in inspector.get_foreign_keys(table_name, schema="public"):
            for local_col in fk["constrained_columns"]:
                ref = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                fk_map[local_col] = ref

        columns = []
        for col in columns_raw:
            col_info = ColumnInfo(
                name=col["name"],
                type=str(col["type"]),
                nullable=col.get("nullable", True),
                primary_key=col["name"] in pk_cols,
                foreign_key=fk_map.get(col["name"]),
                sample_values=_get_sample_values(table_name, col["name"], str(col["type"])),
            )
            columns.append(col_info)

        # Row count
        row_count = _get_row_count(table_name)

        table_info = TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
        )
        schema.tables.append(table_info)

        # Relationships
        for fk in inspector.get_foreign_keys(table_name, schema="public"):
            schema.relationships.append({
                "from_table": table_name,
                "from_columns": fk["constrained_columns"],
                "to_table": fk["referred_table"],
                "to_columns": fk["referred_columns"],
            })

    logger.info("Schema inspection complete", tables=len(schema.tables))
    return schema


def _get_sample_values(table: str, column: str, col_type: str) -> list[Any]:
    """Fetch up to 5 distinct sample values for categorical/text columns."""
    try:
        categorical_types = {"varchar", "text", "character", "enum", "bool", "boolean"}
        if not any(t in col_type.lower() for t in categorical_types):
            return []
        with rw_engine.connect() as conn:
            result = conn.execute(
                text(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT 5')
            )
            return [row[0] for row in result]
    except Exception as e:
        logger.warning("Could not fetch sample values", table=table, column=column, error=str(e))
        return []


def _get_row_count(table: str) -> int:
    try:
        with rw_engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            return result.scalar() or 0
    except Exception:
        return 0


def schema_to_prompt_context(schema: SchemaInfo, relevant_tables: list[str] | None = None) -> str:
    """Convert schema to an LLM-friendly string."""
    tables = schema.tables
    if relevant_tables:
        tables = [t for t in tables if t.name in relevant_tables]

    lines = ["## Database Schema\n"]
    for table in tables:
        lines.append(f"### Table: `{table.name}` ({table.row_count:,} rows)")
        for col in table.columns:
            flags = []
            if col.primary_key:
                flags.append("PK")
            if col.foreign_key:
                flags.append(f"FK → {col.foreign_key}")
            if not col.nullable:
                flags.append("NOT NULL")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            sample_str = f" — e.g. {col.sample_values[:3]}" if col.sample_values else ""
            lines.append(f"  - `{col.name}` {col.type}{flag_str}{sample_str}")
        lines.append("")

    if schema.relationships:
        lines.append("## Relationships")
        for rel in schema.relationships:
            from_cols = ", ".join(rel["from_columns"])
            to_cols = ", ".join(rel["to_columns"])
            lines.append(f"  - `{rel['from_table']}.{from_cols}` → `{rel['to_table']}.{to_cols}`")

    return "\n".join(lines)


def get_all_table_names() -> list[str]:
    schema = get_schema()
    return [t.name for t in schema.tables]


def get_all_column_names(table: str) -> list[str]:
    schema = get_schema()
    for t in schema.tables:
        if t.name == table:
            return [c.name for c in t.columns]
    return []


def schema_to_dict() -> dict:
    """Return schema as a serializable dict for the API."""
    schema = get_schema()
    return {
        "tables": [
            {
                "name": t.name,
                "row_count": t.row_count,
                "columns": [
                    {
                        "name": c.name,
                        "type": c.type,
                        "nullable": c.nullable,
                        "primary_key": c.primary_key,
                        "foreign_key": c.foreign_key,
                        "sample_values": c.sample_values,
                    }
                    for c in t.columns
                ],
            }
            for t in schema.tables
        ],
        "relationships": schema.relationships,
    }
