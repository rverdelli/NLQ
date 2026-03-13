from pydantic import BaseModel
from typing import Any


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class QueryInfo(BaseModel):
    sql: str | None = None
    explanation: str | None = None
    row_count: int | None = None


class ChatResponse(BaseModel):
    reply: str
    chart: dict[str, Any] | None = None
    query_info: QueryInfo | None = None
    suggestions: list[str] = []


class SchemaColumn(BaseModel):
    name: str
    type: str
    description: str
    nullable: bool = True
    references: str | None = None


class SchemaTable(BaseModel):
    name: str
    description: str
    columns: list[SchemaColumn]
    row_count: int


class SchemaResponse(BaseModel):
    tables: list[SchemaTable]
