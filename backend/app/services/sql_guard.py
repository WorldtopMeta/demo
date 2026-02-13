import re
from dataclasses import dataclass


class SQLGuardError(ValueError):
    pass


FORBIDDEN_TOKENS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "execute",
    "call",
    "pg_catalog",
    "information_schema",
]


@dataclass
class GuardedSQL:
    sql: str
    applied_default_limit: bool = False


def _strip_sql(sql: str) -> str:
    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def _contains_disallowed_comment(sql: str) -> bool:
    return "--" in sql or "/*" in sql or "*/" in sql


def _is_select_only(sql: str) -> bool:
    return bool(re.match(r"^\s*select\b", sql, flags=re.IGNORECASE))


def _contains_forbidden_tokens(sql: str) -> str | None:
    lowered = sql.lower()
    for token in FORBIDDEN_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            return token
    return None


def _uses_only_countries_lpi(sql: str) -> bool:
    lowered = sql.lower()
    # Accept direct table or aliased reference, optionally schema-qualified.
    matches = re.findall(r'\b(?:from|join)\s+([\w\.\"]+)', lowered)
    if not matches:
        return False

    allowed = {"countries_lpi", "public.countries_lpi", '"countries_lpi"', '"public"."countries_lpi"'}
    return all(table in allowed for table in matches)


def _is_aggregate_query(sql: str) -> bool:
    lowered = sql.lower()
    return any(keyword in lowered for keyword in ["count(", "avg(", "sum(", "min(", "max(", "group by"])


def guard_sql(sql: str, default_limit: int = 200) -> GuardedSQL:
    cleaned = _strip_sql(sql)

    if not cleaned:
        raise SQLGuardError("LLM did not return a SQL statement.")
    if ";" in cleaned:
        raise SQLGuardError("Only single SQL statement is allowed.")
    if _contains_disallowed_comment(cleaned):
        raise SQLGuardError("SQL comments are not allowed.")
    if not _is_select_only(cleaned):
        raise SQLGuardError("Only SELECT statements are allowed.")

    forbidden = _contains_forbidden_tokens(cleaned)
    if forbidden:
        raise SQLGuardError(f"Forbidden SQL token detected: {forbidden}")

    if not _uses_only_countries_lpi(cleaned):
        raise SQLGuardError("Query must only access countries_lpi.")

    if not _is_aggregate_query(cleaned) and not re.search(r"\blimit\s+\d+\b", cleaned, flags=re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {default_limit}"
        return GuardedSQL(sql=cleaned, applied_default_limit=True)

    return GuardedSQL(sql=cleaned)
