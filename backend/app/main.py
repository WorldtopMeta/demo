from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import QueryRequest, QueryResponse
from app.services.llm_sql import LLMError, generate_sql, normalize_question
from app.services.sql_guard import SQLGuardError, guard_sql
from app.services.supabase_client import SupabaseQueryError, run_sql

settings = get_settings()
app = FastAPI(title="AI Trade Query API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    question = normalize_question(req.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty after normalization.")

    try:
        llm_result = await generate_sql(
            question=question,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
        )
        guarded = guard_sql(llm_result.sql)
        columns, rows = run_sql(settings.supabase_url, settings.supabase_anon_key, guarded.sql)
    except (LLMError, SQLGuardError, SupabaseQueryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meta = {
        "row_count": len(rows),
        "confidence": llm_result.confidence,
        "notes": llm_result.notes,
        "assumptions": llm_result.assumptions,
        "default_limit_applied": guarded.applied_default_limit,
    }

    return QueryResponse(
        sql=guarded.sql,
        columns=columns,
        rows=rows,
        meta=meta,
    )
