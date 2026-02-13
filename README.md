# ai-trade-query (Vue3 + Element Plus + Python)

This project implements a web UI where users ask natural-language trade-data questions. The backend asks an LLM to generate SQL, applies SQL guard rules, fetches `countries_lpi` from Supabase REST (read-only), executes SQL in-memory, and returns table-ready data.

## Project Structure

- `frontend/`: Vue3 + Element Plus UI
- `backend/`: FastAPI API with LLM-to-SQL pipeline

## Data Flow

1. User question from UI
2. `POST /api/query`
3. Normalize input
4. OpenRouter model generates JSON `{ sql, confidence, notes, assumptions }`
5. SQL guard checks:
   - only `SELECT`
   - only `countries_lpi`
   - no comments (`--`, `/* */`)
   - no multi-statement (`;`)
   - block `pg_catalog` / `information_schema`
6. Fetch `countries_lpi` from Supabase REST with anon key
7. Execute guarded SQL in local in-memory SQLite
8. Return `{ sql, columns, rows, meta }`

## Required Queries Covered

- `亞洲哪些國家的 LPI > 3.0`
- `各區域平均 LPI`
- `物流表現前五名` (default: latest year)

## Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Required env vars in `backend/.env`:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (default `openai/gpt-4o-mini`)
- `SUPABASE_URL` (example: `https://bqyrjnpwiwldppbkeafk.supabase.co`)
- `SUPABASE_ANON_KEY` (read-only anon key)
- `CORS_ORIGINS` (default `http://localhost:5173`)

## Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Env var in `frontend/.env`:

- `VITE_API_BASE=http://localhost:8000`

## API Contract

### Request

`POST /api/query`

```json
{ "question": "亞洲哪些國家的 LPI > 3.0" }
```

### Response

```json
{
  "sql": "SELECT ...",
  "columns": ["country", "region", "lpi_score", "year"],
  "rows": [{"country": "..."}],
  "meta": {
    "row_count": 5,
    "confidence": 0.9,
    "notes": "...",
    "assumptions": ["..."],
    "default_limit_applied": false
  }
}
```
