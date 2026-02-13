from typing import Any

from pydantic import BaseModel, Field, conlist


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class QueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    meta: dict[str, Any]


class LLMResult(BaseModel):
    sql: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    notes: str = ""
    assumptions: conlist(str, min_length=0, max_length=6) = Field(default_factory=list)
