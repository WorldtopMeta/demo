import sqlite3
from typing import Any

import httpx


class SupabaseQueryError(RuntimeError):
    pass


_WORD_NUMBERS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


def _normalize_lpi_score(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip().lower()
        try:
            return float(raw)
        except ValueError:
            parts = [_WORD_NUMBERS.get(part, part) for part in raw.split()]
            normalized = "".join("." if part == "point" else part for part in parts)
            try:
                return float(normalized)
            except ValueError:
                return None
    return None


def _fetch_all_rows(supabase_url: str, anon_key: str) -> list[dict[str, Any]]:
    if not supabase_url:
        raise SupabaseQueryError("SUPABASE_URL is missing.")
    if not anon_key:
        raise SupabaseQueryError("SUPABASE_ANON_KEY is missing.")

    base_url = supabase_url.rstrip("/")
    endpoint = f"{base_url}/rest/v1/countries_lpi"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Accept": "application/json",
    }

    all_rows: list[dict[str, Any]] = []
    page_size = 1000
    start = 0

    with httpx.Client(timeout=30) as client:
        while True:
            end = start + page_size - 1
            response = client.get(
                endpoint,
                headers={**headers, "Range": f"{start}-{end}"},
                params={"select": "id,country,region,lpi_score,year", "order": "id.asc"},
            )

            if response.status_code >= 400:
                raise SupabaseQueryError(
                    f"Supabase REST error: {response.status_code} {response.text}"
                )

            batch = response.json()
            if not isinstance(batch, list):
                raise SupabaseQueryError("Unexpected Supabase response format.")

            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            start += page_size

    return all_rows


def _execute_sql_locally(rows: list[dict[str, Any]], sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE countries_lpi (
                id INTEGER,
                country TEXT,
                region TEXT,
                lpi_score REAL,
                year INTEGER
            )
            """
        )

        cur.executemany(
            """
            INSERT INTO countries_lpi (id, country, region, lpi_score, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row.get("id"),
                    row.get("country"),
                    row.get("region"),
                    _normalize_lpi_score(row.get("lpi_score")),
                    row.get("year"),
                )
                for row in rows
            ],
        )

        cur.execute(sql)
        fetched = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return columns, [dict(record) for record in fetched]
    except Exception as exc:
        raise SupabaseQueryError(f"SQL execution error: {exc}") from exc
    finally:
        conn.close()


def run_sql(supabase_url: str, anon_key: str, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    rows = _fetch_all_rows(supabase_url=supabase_url, anon_key=anon_key)
    return _execute_sql_locally(rows=rows, sql=sql)
