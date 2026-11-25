# ===============================================
# File: backend/reporting/filter_sql.py
# Description: Restricted SQL predicate validation for Report Generator
# Modified: 2026-11-26 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import re
from typing import Any

from fastapi import HTTPException


_TOKEN_PATTERN = re.compile(
    r"""
    (?P<space>\s+)
    |(?P<string>'(?:''|[^'])*')
    |(?P<quoted>"(?:""|[^"])+")
    |(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
    |(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)
    |(?P<operator><=|>=|<>|!=|=|<|>|\|\||\+|-|\*|/|%)
    |(?P<punct>[(),])
    |(?P<invalid>.)
    """,
    re.VERBOSE | re.DOTALL,
)

_KEYWORDS = {
    "AND", "OR", "NOT", "IS", "NULL", "TRUE", "FALSE",
    "LIKE", "ILIKE", "IN", "BETWEEN", "DATE", "TIME",
    "TIMESTAMP", "INTERVAL", "CURRENT_DATE", "CURRENT_TIME",
    "CURRENT_TIMESTAMP", "ESCAPE",
}

_SAFE_FUNCTIONS = {
    "ABS", "CEIL", "CEILING", "FLOOR", "ROUND",
    "LOWER", "UPPER", "TRIM", "BTRIM", "LTRIM", "RTRIM",
    "LENGTH", "CHAR_LENGTH", "COALESCE", "NULLIF",
}


def validate_sql_filter(
    expression: str,
    field_metadata: dict[str, dict[str, Any]],
) -> str:
    """Validate a predicate-only SQL expression against searchable Grid fields."""
    source = (expression or "").strip()

    if not source or len(source) > 4000:
        raise HTTPException(
            status_code=422,
            detail="SQL Filter must contain between 1 and 4000 characters.",
        )

    if any(marker in source for marker in (";", "--", "/*", "*/", ":", "#")):
        raise HTTPException(
            status_code=422,
            detail="SQL Filter cannot contain comments, bind markers, or statement separators.",
        )

    searchable_fields = {
        name
        for name, metadata in field_metadata.items()
        if metadata.get("visible_in_search") is True
    }

    tokens: list[tuple[str, str]] = []
    position = 0

    while position < len(source):
        match = _TOKEN_PATTERN.match(source, position)
        if match is None:
            raise HTTPException(status_code=422, detail="Invalid SQL Filter token.")

        kind = match.lastgroup
        value = match.group()

        if kind == "space":
            position = match.end()
            continue

        if kind == "invalid":
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported SQL Filter character: {value}",
            )

        if value == ";" or "--" in value or "/*" in value or "*/" in value:
            raise HTTPException(
                status_code=422,
                detail="SQL Filter cannot contain statement separators or comments.",
            )

        tokens.append((kind or "", value))
        position = match.end()

    normalized: list[str] = []
    depth = 0

    for index, (kind, value) in enumerate(tokens):
        upper = value.upper()

        if kind == "string" or kind == "number":
            normalized.append(value)
            continue

        if kind == "quoted":
            field_name = value[1:-1].replace('""', '"')
            if field_name not in searchable_fields:
                raise HTTPException(
                    status_code=403,
                    detail=f"SQL Filter field '{field_name}' is not searchable in this Grid.",
                )
            normalized.append('"' + field_name.replace('"', '""') + '"')
            continue

        if kind == "identifier":
            if upper in _KEYWORDS:
                normalized.append(upper)
                continue

            next_value = tokens[index + 1][1] if index + 1 < len(tokens) else ""
            if next_value == "(":
                if upper not in _SAFE_FUNCTIONS:
                    raise HTTPException(
                        status_code=403,
                        detail=f"SQL Filter function '{value}' is not allowed.",
                    )
                normalized.append(upper)
                continue

            if value not in searchable_fields:
                raise HTTPException(
                    status_code=403,
                    detail=f"SQL Filter field or keyword '{value}' is not allowed.",
                )

            normalized.append('"' + value.replace('"', '""') + '"')
            continue

        if kind == "punct":
            if value == "(":
                depth += 1
            elif value == ")":
                depth -= 1
                if depth < 0:
                    raise HTTPException(
                        status_code=422,
                        detail="SQL Filter parentheses are unbalanced.",
                    )
            normalized.append(value)
            continue

        if kind == "operator":
            normalized.append(value)
            continue

        raise HTTPException(
            status_code=422,
            detail="Unsupported SQL Filter syntax.",
        )

    if depth != 0:
        raise HTTPException(
            status_code=422,
            detail="SQL Filter parentheses are unbalanced.",
        )

    safe_expression = " ".join(normalized)

    if not safe_expression:
        raise HTTPException(status_code=422, detail="SQL Filter cannot be empty.")

    return safe_expression
