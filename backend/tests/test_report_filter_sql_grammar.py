# ===============================================
# File: backend/tests/test_report_filter_sql_grammar.py
# Description: PostgreSQL grammar and function-arity tests for Report Generator filters
# Modified: 2026-11-26 05:00 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import pytest

from fastapi import HTTPException

from reporting.filter_sql import validate_sql_filter


FIELD_METADATA = {
    "AGE": {"visible_in_search": True},
    "NAME": {"visible_in_search": True},
    "STATUS": {"visible_in_search": True},
}


@pytest.mark.parametrize(
    "expression",
    [
        "AGE >",
        "AND AGE = 10",
        "AGE = = 10",
        "AGE IN ()",
        "AGE BETWEEN 1",
        "LOWER() = 'x'",
        "AGE = 10 OR",
        "NOT",
        "AGE + = 2",
    ],
)
def test_invalid_predicate_grammar_is_rejected(expression):
    with pytest.raises(HTTPException) as exc_info:
        validate_sql_filter(expression, FIELD_METADATA)

    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    "expression",
    [
        "AGE >= 18",
        "AGE >= 18 AND STATUS = 'ACTIVE'",
        "NAME IS NOT NULL",
        "AGE BETWEEN 18 AND 65",
        "AGE IN (18, 25, 30)",
        "LOWER(NAME) = 'hamid'",
        "ROUND(AGE, 2) >= 18",
        "COALESCE(STATUS, 'UNKNOWN') = 'ACTIVE'",
        "COALESCE(LOWER(NAME), 'unknown') = 'hamid'",
    ],
)
def test_valid_predicate_grammar_is_accepted(expression):
    result = validate_sql_filter(expression, FIELD_METADATA)

    assert result


@pytest.mark.parametrize(
    "expression",
    [
        "LOWER() = 'x'",
        "ABS(AGE, 2) > 1",
        "COALESCE(STATUS) = 'ACTIVE'",
        "NULLIF(AGE) = 0",
    ],
)
def test_invalid_safe_function_arity_is_rejected(expression):
    with pytest.raises(HTTPException) as exc_info:
        validate_sql_filter(expression, FIELD_METADATA)

    assert exc_info.value.status_code == 422
