import json
import re
from typing import Any

import httpx

from app.models import LLMResult


PROMPT = """
You are a SQL generator for PostgreSQL.

Hard rules:
1) Output JSON only with keys: sql, confidence, notes, assumptions.
1.1) confidence must be a number between 0 and 1 (not words like high/medium/low).
1.2) assumptions must be an array of strings. Use [] when none.
2) sql must be a single SELECT statement querying only countries_lpi(id, country, region, lpi_score, year).
3) Never use INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE.
4) Never query other tables, pg_catalog, information_schema.
5) Never output comments or multiple statements.
6) For non-aggregate queries, include LIMIT <= 200.
7) If user asks top 5 and data spans years, default to latest year with WHERE year = (SELECT MAX(year) FROM countries_lpi).
8) If user asks about Asia and region values may vary, prefer case-insensitive filter: LOWER(region) = 'asia'.
9) If region names look inconsistent, include a note suggesting: SELECT DISTINCT region FROM countries_lpi.

Examples:
- Asia countries with LPI > 3.0:
  SELECT country, region, lpi_score, year
  FROM countries_lpi
  WHERE LOWER(region) = 'asia' AND lpi_score > 3.0
  ORDER BY lpi_score DESC
  LIMIT 200
- Average LPI by region:
  SELECT region, AVG(lpi_score) AS avg_lpi_score
  FROM countries_lpi
  GROUP BY region
  ORDER BY avg_lpi_score DESC
- Top five logistics performers:
  SELECT country, region, lpi_score, year
  FROM countries_lpi
  WHERE year = (SELECT MAX(year) FROM countries_lpi)
  ORDER BY lpi_score DESC
  LIMIT 5
""".strip()


class LLMError(RuntimeError):
    pass


def _normalize_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(max(0.0, min(1.0, value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        mapping = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3,
        }
        if lowered in mapping:
            return mapping[lowered]
        try:
            parsed = float(lowered)
            return float(max(0.0, min(1.0, parsed)))
        except ValueError:
            return 0.0
    return 0.0


def _normalize_assumptions(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:6]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def _normalize_llm_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    sql = str(parsed.get("sql", "")).strip()
    notes = str(parsed.get("notes", "")).strip()
    confidence = _normalize_confidence(parsed.get("confidence", 0.0))
    assumptions = _normalize_assumptions(parsed.get("assumptions", []))
    return {
        "sql": sql,
        "confidence": confidence,
        "notes": notes,
        "assumptions": assumptions,
    }


def normalize_question(question: str) -> str:
    cleaned = question.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"(?i)(ignore previous instructions|system prompt|developer mode)", "", cleaned)
    return cleaned[:500]


async def generate_sql(
    *,
    question: str,
    api_key: str,
    model: str,
) -> LLMResult:
    if not api_key:
        raise LLMError("OPENROUTER_API_KEY is missing.")

    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": question},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code >= 400:
        raise LLMError(f"OpenRouter error: {response.status_code} {response.text}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        normalized = _normalize_llm_payload(parsed)
        return LLMResult(**normalized)
    except Exception as exc:
        raise LLMError(f"Unable to parse LLM output: {exc}") from exc
