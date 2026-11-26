# ===============================================
# File: backend/tests/test_grid_personalization.py
# Description: Validation tests for personal Grid preferences
# Modified: 2026-11-26 15:04 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import pytest
from fastapi import HTTPException

from general.config.routes import (
    _validate_grid_layout,
    _validate_grid_search_filters,
)


FIELD_METADATA = {
    "c_id": {
        "visible_in_grid": True,
        "visible_in_search": True,
    },
    "c_name": {
        "visible_in_grid": True,
        "visible_in_search": True,
    },
    "c_internal": {
        "visible_in_grid": False,
        "visible_in_search": False,
    },
}


def test_grid_layout_accepts_order_width_visibility_and_header_height():
    result = _validate_grid_layout(
        {
            "column_order": ["c_name", "c_id"],
            "column_widths": {"c_name": 320},
            "hidden_columns": ["c_id"],
            "header_height_px": 72,
        },
        FIELD_METADATA,
    )

    assert result == {
        "column_order": ["c_name", "c_id"],
        "column_widths": {"c_name": 320},
        "hidden_columns": ["c_id"],
        "header_height_px": 72,
    }


def test_grid_layout_rejects_unknown_fields():
    with pytest.raises(HTTPException) as error:
        _validate_grid_layout(
            {"column_order": ["c_internal"]},
            FIELD_METADATA,
        )

    assert error.value.status_code == 422


def test_grid_layout_requires_at_least_one_visible_column():
    with pytest.raises(HTTPException) as error:
        _validate_grid_layout(
            {"hidden_columns": ["c_id", "c_name"]},
            FIELD_METADATA,
        )

    assert error.value.status_code == 422


def test_grid_layout_rejects_out_of_range_width():
    with pytest.raises(HTTPException) as error:
        _validate_grid_layout(
            {"column_widths": {"c_name": 20}},
            FIELD_METADATA,
        )

    assert error.value.status_code == 422


def test_grid_search_filters_accept_only_searchable_fields():
    result = _validate_grid_search_filters(
        {
            "c_name": {
                "from": "Hamid",
                "to": "",
            }
        },
        FIELD_METADATA,
    )

    assert result == {
        "c_name": {
            "from": "Hamid",
            "to": "",
        }
    }


def test_grid_search_filters_reject_hidden_search_fields():
    with pytest.raises(HTTPException) as error:
        _validate_grid_search_filters(
            {"c_internal": {"from": "x"}},
            FIELD_METADATA,
        )

    assert error.value.status_code == 422


def test_grid_search_filters_drop_empty_ranges():
    result = _validate_grid_search_filters(
        {
            "c_name": {
                "from": "",
                "to": None,
            }
        },
        FIELD_METADATA,
    )

    assert result == {}
