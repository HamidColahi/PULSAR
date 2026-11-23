# ===============================================
# File: backend/reporting/routes.py
# Description: Metadata-driven Report Generator API
# Modified: 2026-11-24 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from typing import Any, Literal
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_context import get_audited_session
from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse
from general.permissions.service import (
    require_page_view_access,
    require_permission,
)
from reporting.service import (
    DYNAMIC_PARAMETERS,
    FILTER_OPERATORS,
    execute_report,
    json_safe,
    load_report,
    load_report_definition,
    require_report_delete_access,
    require_report_edit_access,
    require_report_view_access,
    replace_report_definition,
    validate_report_page,
)


router = APIRouter(
    prefix="/reports",
    tags=["Report Generator"],
)


class ReportColumnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=255)
    display_order: int = Field(ge=1)
    width_px: int | None = Field(default=None, ge=24, le=2000)
    is_visible: bool = True
    sort_direction: Literal["asc", "desc"] | None = None
    sort_order: int | None = Field(default=None, ge=1)


class ReportFilterNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_type: Literal["GROUP", "CONDITION"]
    logical_operator: Literal["AND", "OR"] | None = None
    field_name: str | None = Field(default=None, max_length=255)
    operator_code: str | None = Field(default=None, max_length=40)
    value: Any = None
    parameter_code: str | None = Field(default=None, max_length=40)
    display_order: int = Field(default=1, ge=1)
    children: list["ReportFilterNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.node_type == "GROUP":
            if self.logical_operator not in ("AND", "OR"):
                raise ValueError("A filter group requires AND or OR.")
            if not self.children:
                raise ValueError("A filter group requires at least one child.")
            if self.field_name or self.operator_code or self.parameter_code:
                raise ValueError("A filter group cannot contain condition fields.")
        else:
            if not self.field_name or not self.operator_code:
                raise ValueError("A filter condition requires a field and operator.")
            if self.logical_operator is not None or self.children:
                raise ValueError("A filter condition cannot contain group properties.")
            self.operator_code = self.operator_code.upper()
            if self.operator_code not in FILTER_OPERATORS:
                raise ValueError("Unsupported report filter operator.")
            if self.parameter_code is not None:
                self.parameter_code = self.parameter_code.upper()
                if self.parameter_code not in DYNAMIC_PARAMETERS:
                    raise ValueError("Unsupported report dynamic parameter.")
            elif self.operator_code not in ("IS_NULL", "IS_NOT_NULL") and self.value is None:
                raise ValueError("A filter condition requires a value or dynamic parameter.")
        return self


ReportFilterNode.model_rebuild()


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_key: str = Field(min_length=1, max_length=255)
    source_component_name: str = Field(min_length=1, max_length=255)
    report_title: str = Field(min_length=1, max_length=255)
    report_desc: str | None = Field(default=None, max_length=4000)
    columns: list[ReportColumnInput] = Field(default_factory=list)
    filters: list[ReportFilterNode] = Field(default_factory=list)


class ReportPreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_key: str = Field(min_length=1, max_length=255)
    source_component_name: str = Field(min_length=1, max_length=255)
    columns: list[ReportColumnInput] = Field(default_factory=list)
    filters: list[ReportFilterNode] = Field(default_factory=list)
    selected_record: dict[str, Any] = Field(default_factory=dict)
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)


class ReportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_title: str | None = Field(default=None, min_length=1, max_length=255)
    report_desc: str | None = Field(default=None, max_length=4000)
    columns: list[ReportColumnInput] | None = None
    filters: list[ReportFilterNode] | None = None


class ReportClone(BaseModel):
    report_title: str | None = Field(default=None, min_length=1, max_length=255)


class ReportShareInput(BaseModel):
    target_user_id: UUID
    permission_level: Literal["VIEW", "EDIT"] = "VIEW"


class ReportRunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_record: dict[str, Any] = Field(default_factory=dict)
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)


class ReportPageConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_enabled: bool
    allow_sharing: bool = True
    allow_public: bool = False

    @model_validator(mode="after")
    def validate_options(self):
        if self.allow_public and not self.is_enabled:
            raise ValueError("Public reports require Report Generator to be enabled.")
        return self


async def _load_field_metadata(
    session: AsyncSession,
    component_name: str,
) -> dict[str, dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
                field_name,
                visible_in_grid,
                visible_in_search,
                field_sort,
                field_sort_order,
                ordering_index
            FROM pulsar.components_config
            WHERE component_name = :component_name
              AND field_mode = 'list'
            """
        ),
        {"component_name": component_name},
    )
    return {
        row["field_name"]: dict(row)
        for row in result.mappings().all()
    }


def _validate_columns(
    columns: list[ReportColumnInput],
    field_metadata: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not columns:
        columns = [
            ReportColumnInput(
                field_name=field_name,
                display_order=index,
                is_visible=True,
            )
            for index, (field_name, _) in enumerate(
                sorted(
                    (
                        (name, metadata)
                        for name, metadata in field_metadata.items()
                        if metadata.get("visible_in_grid") is True
                    ),
                    key=lambda item: (
                        item[1].get("ordering_index") or 0,
                        item[0],
                    ),
                ),
                start=1,
            )
        ]

    field_names = [column.field_name for column in columns]
    display_orders = [column.display_order for column in columns]

    if len(field_names) != len(set(field_names)):
        raise HTTPException(
            status_code=422,
            detail="A report field can appear only once.",
        )

    if len(display_orders) != len(set(display_orders)):
        raise HTTPException(
            status_code=422,
            detail="Report column display orders must be unique.",
        )

    normalized = []

    for column in columns:
        metadata = field_metadata.get(column.field_name)

        if metadata is None or metadata.get("visible_in_grid") is not True:
            raise HTTPException(
                status_code=403,
                detail=f"Field '{column.field_name}' is not visible in this Grid.",
            )

        sort_mode = int(metadata.get("field_sort") or 0)

        if column.sort_direction is not None:
            if sort_mode != 1:
                raise HTTPException(
                    status_code=403,
                    detail=f"User sorting is not enabled for field '{column.field_name}'.",
                )
            if column.sort_order is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Sort order is required for field '{column.field_name}'.",
                )
        elif column.sort_order is not None:
            raise HTTPException(
                status_code=422,
                detail=f"Sort direction is required for field '{column.field_name}'.",
            )

        normalized.append(column.model_dump())

    if not any(item["is_visible"] for item in normalized):
        raise HTTPException(
            status_code=422,
            detail="At least one report column must be visible.",
        )

    sort_orders = [
        item["sort_order"]
        for item in normalized
        if item["sort_order"] is not None
    ]

    if len(sort_orders) != len(set(sort_orders)):
        raise HTTPException(
            status_code=422,
            detail="Report sort orders must be unique.",
        )

    return normalized


def _validate_filters(
    filters: list[ReportFilterNode],
    field_metadata: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    def validate_node(node: ReportFilterNode, depth: int = 1) -> dict[str, Any]:
        if depth > 12:
            raise HTTPException(
                status_code=422,
                detail="Report filter nesting exceeds the supported depth.",
            )

        if node.node_type == "GROUP":
            return {
                "node_type": "GROUP",
                "logical_operator": node.logical_operator,
                "display_order": node.display_order,
                "children": [
                    validate_node(child, depth + 1)
                    for child in node.children
                ],
            }

        metadata = field_metadata.get(node.field_name)

        if metadata is None or metadata.get("visible_in_search") is not True:
            raise HTTPException(
                status_code=403,
                detail=f"Filtering is not enabled for field '{node.field_name}'.",
            )

        if node.operator_code not in FILTER_OPERATORS:
            raise HTTPException(
                status_code=422,
                detail="Unsupported report filter operator.",
            )

        return {
            "node_type": "CONDITION",
            "field_name": node.field_name,
            "operator_code": node.operator_code,
            "value": node.value,
            "parameter_code": node.parameter_code,
            "display_order": node.display_order,
            "children": [],
        }

    return [
        validate_node(node)
        for node in filters
    ]


async def _create_report_version(
    session: AsyncSession,
    report_id: UUID,
    user_id: str,
    change_note: str,
) -> None:
    report_result = await session.execute(
        text(
            """
            SELECT
                report_id,
                page_key,
                source_component_name,
                owner_user_id,
                report_title,
                report_desc,
                sharing_policy,
                current_version
            FROM pulsar.t_report
            WHERE report_id = :report_id
            """
        ),
        {"report_id": str(report_id)},
    )
    report = dict(report_result.mappings().one())

    definition = await load_report_definition(
        session,
        report_id,
    )

    snapshot = {
        **report,
        "owner_user_id": str(report["owner_user_id"]),
        "columns": definition["columns"],
        "filters": definition["filters"],
    }

    await session.execute(
        text(
            """
            INSERT INTO pulsar.t_report_version
            (
                report_id,
                version_no,
                definition_snapshot,
                changed_by,
                changed_at,
                change_note
            )
            VALUES
            (
                :report_id,
                :version_no,
                CAST(:definition_snapshot AS JSONB),
                :changed_by,
                CURRENT_TIMESTAMP,
                :change_note
            )
            """
        ),
        {
            "report_id": str(report_id),
            "version_no": report["current_version"],
            "definition_snapshot": json.dumps(
                json_safe(snapshot),
                ensure_ascii=False,
                default=str,
            ),
            "changed_by": user_id,
            "change_note": change_note,
        },
    )


async def _require_report_page_option(
    session: AsyncSession,
    page_key: str,
    option_name: str,
) -> None:
    if option_name not in {"allow_sharing", "allow_public"}:
        raise ValueError("Unsupported Report Generator page option.")

    result = await session.execute(
        text(
            f"""
            SELECT 1
            FROM pulsar.t_report_page_config
            WHERE page_key = :page_key
              AND is_enabled IS TRUE
              AND {option_name} IS TRUE
            """
        ),
        {"page_key": page_key},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=403,
            detail=f"Report Generator option '{option_name}' is disabled for this page.",
        )


async def _load_target_user(
    session: AsyncSession,
    user_id: UUID,
) -> None:
    result = await session.execute(
        text(
            """
            SELECT c_user_id
            FROM pulsar.t_user
            WHERE c_user_id = :user_id
              AND c_user_active IS TRUE
            """
        ),
        {"user_id": str(user_id)},
    )

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail="The target user does not exist or is inactive.",
        )


@router.get("/config/pages")
async def list_report_page_configuration(
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """List Report Generator configuration for every dynamic page."""
    await require_permission(
        session,
        str(current_user.id),
        "SECURITY.PERMISSION.GRANT",
        None,
    )

    result = await session.execute(
        text(
            """
            SELECT
                page.page_key,
                page.page_type,
                page.page_level,
                page."Page_desc" AS page_desc,
                COALESCE(config.is_enabled, FALSE) AS is_enabled,
                COALESCE(config.allow_sharing, TRUE) AS allow_sharing,
                COALESCE(config.allow_public, FALSE) AS allow_public,
                config.created_by,
                config.created_at,
                config.updated_by,
                config.updated_at
            FROM pulsar.dynamic_page page
            LEFT JOIN pulsar.t_report_page_config config
                ON config.page_key = page.page_key
            ORDER BY page.page_key
            """
        )
    )
    return [
        {
            **dict(row),
            "created_by": str(row["created_by"]) if row["created_by"] else None,
            "updated_by": str(row["updated_by"]) if row["updated_by"] else None,
        }
        for row in result.mappings().all()
    ]


@router.put("/config/pages/{page_key}")
async def update_report_page_configuration(
    page_key: str,
    payload: ReportPageConfigUpdate,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Enable or disable Report Generator features for one dynamic page."""
    await require_permission(
        session,
        str(current_user.id),
        "SECURITY.PERMISSION.GRANT",
        None,
    )

    page_result = await session.execute(
        text("SELECT page_key FROM pulsar.dynamic_page WHERE page_key = :page_key"),
        {"page_key": page_key},
    )
    if page_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="PULSAR page was not found.")

    await session.execute(
        text(
            """
            INSERT INTO pulsar.t_report_page_config
            (
                page_key,
                is_enabled,
                allow_sharing,
                allow_public,
                created_by,
                created_at,
                updated_by,
                updated_at
            )
            VALUES
            (
                :page_key,
                :is_enabled,
                :allow_sharing,
                :allow_public,
                :user_id,
                CURRENT_TIMESTAMP,
                :user_id,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (page_key)
            DO UPDATE SET
                is_enabled = EXCLUDED.is_enabled,
                allow_sharing = EXCLUDED.allow_sharing,
                allow_public = EXCLUDED.allow_public,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "page_key": page_key,
            "is_enabled": payload.is_enabled,
            "allow_sharing": payload.allow_sharing,
            "allow_public": payload.allow_public,
            "user_id": str(current_user.id),
        },
    )

    if payload.is_enabled:
        permission_definitions = [
            ("REPORT.DESIGN.EDIT", "Edit users reports", "Edit reports created by other users for this page."),
            ("REPORT.DESIGN.DELETE", "Delete users reports", "Delete reports created by other users for this page."),
        ]
        if payload.allow_public:
            permission_definitions.append(
                ("REPORT.PUBLIC.PUBLISH", "Publish public reports", "Publish reports as public for this Report Generator page.")
            )

        for code, title, description in permission_definitions:
            await session.execute(
                text(
                    """
                    INSERT INTO pulsar.t_permission
                    (
                        permission_code,
                        permission_title,
                        page_key,
                        scope_type,
                        scope_key,
                        permission_desc,
                        is_active,
                        created_by,
                        created_at
                    )
                    VALUES
                    (
                        :permission_code,
                        :permission_title,
                        :page_key,
                        'PAGE',
                        :page_key,
                        :permission_desc,
                        TRUE,
                        :user_id,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "permission_code": code,
                    "permission_title": title,
                    "page_key": page_key,
                    "permission_desc": description,
                    "user_id": str(current_user.id),
                },
            )

    await session.execute(
        text(
            """
            UPDATE pulsar.t_permission
            SET
                is_active = CASE
                    WHEN :is_enabled IS FALSE THEN FALSE
                    WHEN permission_code = 'REPORT.PUBLIC.PUBLISH' THEN :allow_public
                    ELSE TRUE
                END,
                updated_by = :user_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE page_key = :page_key
              AND permission_code IN (
                    'REPORT.PUBLIC.PUBLISH',
                    'REPORT.DESIGN.EDIT',
                    'REPORT.DESIGN.DELETE'
              )
            """
        ),
        {
            "page_key": page_key,
            "is_enabled": payload.is_enabled,
            "allow_public": payload.allow_public,
            "user_id": str(current_user.id),
        },
    )

    await session.commit()
    return {
        "page_key": page_key,
        "is_enabled": payload.is_enabled,
        "allow_sharing": payload.allow_sharing,
        "allow_public": payload.allow_public,
    }


@router.get("/pages/{page_key}/configuration")
async def read_report_page_configuration(
    page_key: str,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Return the Report Generator feature flags for a page visible to the caller."""
    await require_page_view_access(
        session,
        str(current_user.id),
        page_key,
    )

    result = await session.execute(
        text(
            """
            SELECT
                page.page_key,
                COALESCE(config.is_enabled, FALSE) AS is_enabled,
                COALESCE(config.allow_sharing, TRUE) AS allow_sharing,
                COALESCE(config.allow_public, FALSE) AS allow_public
            FROM pulsar.dynamic_page page
            LEFT JOIN pulsar.t_report_page_config config
                ON config.page_key = page.page_key
            WHERE page.page_key = :page_key
            """
        ),
        {"page_key": page_key},
    )
    config = result.mappings().first()
    if config is None:
        raise HTTPException(status_code=404, detail="PULSAR page was not found.")

    return dict(config)


@router.get("/pages/{page_key}")
async def list_page_reports(
    page_key: str,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """List the authenticated user's own, shared, and public reports for a Report.Gen page."""
    await require_page_view_access(
        session,
        str(current_user.id),
        page_key,
    )

    page_result = await session.execute(
        text(
            """
            SELECT is_enabled, allow_public
            FROM pulsar.t_report_page_config
            WHERE page_key = :page_key
            """
        ),
        {"page_key": page_key},
    )
    page_config = page_result.mappings().first()

    if page_config is None or page_config["is_enabled"] is not True:
        raise HTTPException(
            status_code=404,
            detail="Report Generator is not enabled for this page.",
        )

    result = await session.execute(
        text(
            """
            SELECT
                report.report_id,
                report.page_key,
                report.source_component_name,
                report.owner_user_id,
                report.report_title,
                report.report_desc,
                report.sharing_policy,
                report.current_version,
                report.updated_at,
                CASE
                    WHEN report.owner_user_id = :user_id THEN 'OWNER'
                    WHEN share.permission_level = 'EDIT' THEN 'SHARED_EDIT'
                    WHEN share.permission_level = 'VIEW' THEN 'SHARED_VIEW'
                    ELSE 'PUBLIC_VIEW'
                END AS access_mode
            FROM pulsar.t_report report
            INNER JOIN pulsar.t_report_page_config page_config
                ON page_config.page_key = report.page_key
               AND page_config.is_enabled IS TRUE
            LEFT JOIN pulsar.t_report_share share
                ON share.report_id = report.report_id
               AND share.target_user_id = :user_id
               AND share.is_active IS TRUE
            WHERE report.page_key = :page_key
              AND report.is_active IS TRUE
              AND (
                    report.owner_user_id = :user_id
                    OR (
                        report.sharing_policy = 'PUBLIC'
                        AND page_config.allow_public IS TRUE
                    )
                    OR (
                        report.sharing_policy = 'SHARED'
                        AND share.share_id IS NOT NULL
                    )
              )
            ORDER BY
                CASE WHEN report.owner_user_id = :user_id THEN 0 ELSE 1 END,
                report.updated_at DESC,
                report.report_title
            """
        ),
        {
            "page_key": page_key,
            "user_id": str(current_user.id),
        },
    )

    return [
        {
            **dict(row),
            "report_id": str(row["report_id"]),
            "owner_user_id": str(row["owner_user_id"]),
        }
        for row in result.mappings().all()
    ]


@router.post("/preview")
async def preview_report(
    payload: ReportPreviewInput,
    request: Request,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Preview an unsaved report definition using the current user's data scope."""
    await validate_report_page(
        session,
        str(current_user.id),
        payload.page_key,
        payload.source_component_name,
    )

    field_metadata = await _load_field_metadata(
        session,
        payload.source_component_name,
    )
    columns = _validate_columns(payload.columns, field_metadata)
    filters = _validate_filters(payload.filters, field_metadata)

    preview_report_definition = {
        "report_id": UUID(int=0),
        "page_key": payload.page_key,
        "source_component_name": payload.source_component_name,
    }

    return await execute_report(
        session,
        request,
        preview_report_definition,
        {
            "columns": columns,
            "filters": filters,
        },
        user_id=str(current_user.id),
        profile_id=str(current_user.profile_id),
        selected_record=payload.selected_record,
        runtime_context=payload.runtime_context,
        limit=payload.limit,
        offset=payload.offset,
    )


@router.post("", status_code=201)
async def create_report(
    payload: ReportCreate,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Create a private report bound to a Report.Gen page and one list component."""
    await validate_report_page(
        session,
        str(current_user.id),
        payload.page_key,
        payload.source_component_name,
    )

    field_metadata = await _load_field_metadata(
        session,
        payload.source_component_name,
    )
    columns = _validate_columns(payload.columns, field_metadata)
    filters = _validate_filters(payload.filters, field_metadata)

    result = await session.execute(
        text(
            """
            INSERT INTO pulsar.t_report
            (
                page_key,
                source_component_name,
                owner_user_id,
                report_title,
                report_desc,
                sharing_policy,
                is_active,
                current_version,
                created_at,
                updated_at
            )
            VALUES
            (
                :page_key,
                :source_component_name,
                :owner_user_id,
                :report_title,
                :report_desc,
                'PRIVATE',
                TRUE,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING report_id
            """
        ),
        {
            "page_key": payload.page_key,
            "source_component_name": payload.source_component_name,
            "owner_user_id": str(current_user.id),
            "report_title": payload.report_title.strip(),
            "report_desc": payload.report_desc,
        },
    )

    report_id = UUID(str(result.scalar_one()))

    await replace_report_definition(
        session,
        report_id,
        columns,
        filters,
        user_id=str(current_user.id),
    )

    await _create_report_version(
        session,
        report_id,
        str(current_user.id),
        "Initial report definition",
    )

    await session.commit()

    return {
        "report_id": str(report_id),
        "page_key": payload.page_key,
        "source_component_name": payload.source_component_name,
        "report_title": payload.report_title.strip(),
        "sharing_policy": "PRIVATE",
        "current_version": 1,
    }


@router.get("/{report_id}")
async def read_report(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)
    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await require_report_view_access(
        session,
        report,
        str(current_user.id),
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )

    definition = await load_report_definition(
        session,
        report_id,
    )

    return {
        **report,
        "report_id": str(report["report_id"]),
        "owner_user_id": str(report["owner_user_id"]),
        **definition,
    }


@router.put("/{report_id}")
async def update_report(
    report_id: UUID,
    payload: ReportUpdate,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(
        session,
        report_id,
        for_update=True,
    )

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_sharing")
    await require_report_edit_access(
        session,
        report,
        str(current_user.id),
    )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=422,
            detail="No report changes were supplied.",
        )

    if "report_title" in changes:
        title = (changes["report_title"] or "").strip()
        if not title:
            raise HTTPException(
                status_code=422,
                detail="Report title cannot be empty.",
            )
        changes["report_title"] = title

    if "columns" in changes or "filters" in changes:
        field_metadata = await _load_field_metadata(
            session,
            report["source_component_name"],
        )
        current_definition = await load_report_definition(
            session,
            report_id,
        )

        columns = (
            _validate_columns(changes["columns"], field_metadata)
            if "columns" in changes
            else current_definition["columns"]
        )
        filters = (
            _validate_filters(changes["filters"], field_metadata)
            if "filters" in changes
            else current_definition["filters"]
        )

        await replace_report_definition(
            session,
            report_id,
            columns,
            filters,
            user_id=str(current_user.id),
        )

    if "report_title" in changes or "report_desc" in changes:
        await session.execute(
            text(
                """
                UPDATE pulsar.t_report
                SET
                    report_title = :report_title,
                    report_desc = :report_desc,
                    updated_at = CURRENT_TIMESTAMP,
                    current_version = current_version + 1
                WHERE report_id = :report_id
                """
            ),
            {
                "report_id": str(report_id),
                "report_title": changes.get("report_title", report["report_title"]),
                "report_desc": changes.get("report_desc", report["report_desc"]),
            },
        )
    elif "columns" in changes or "filters" in changes:
        await session.execute(
            text(
                """
                UPDATE pulsar.t_report
                SET
                    updated_at = CURRENT_TIMESTAMP,
                    current_version = current_version + 1
                WHERE report_id = :report_id
                """
            ),
            {"report_id": str(report_id)},
        )

    await _create_report_version(
        session,
        report_id,
        str(current_user.id),
        "Report definition updated",
    )

    await session.commit()

    updated_report = await load_report(session, report_id)
    definition = await load_report_definition(session, report_id)

    return {
        **updated_report,
        "report_id": str(updated_report["report_id"]),
        **definition,
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(
        session,
        report_id,
        for_update=True,
    )

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await require_report_delete_access(
        session,
        report,
        str(current_user.id),
    )

    await session.execute(
        text(
            """
            UPDATE pulsar.t_report
            SET
                is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE report_id = :report_id
            """
        ),
        {"report_id": str(report_id)},
    )

    await session.commit()

    return {
        "report_id": str(report_id),
        "is_active": False,
    }


@router.post("/{report_id}/clone", status_code=201)
async def clone_report(
    report_id: UUID,
    payload: ReportClone,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    source = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        source["page_key"],
    )
    await require_report_view_access(
        session,
        source,
        str(current_user.id),
    )
    await validate_report_page(
        session,
        str(current_user.id),
        source["page_key"],
        source["source_component_name"],
    )

    source_definition = await load_report_definition(
        session,
        report_id,
    )

    title = (
        payload.report_title.strip()
        if payload.report_title
        else f'{source["report_title"]} Copy'
    )
    if not title:
        raise HTTPException(
            status_code=422,
            detail="Report title cannot be empty.",
        )

    result = await session.execute(
        text(
            """
            INSERT INTO pulsar.t_report
            (
                page_key,
                source_component_name,
                owner_user_id,
                report_title,
                report_desc,
                sharing_policy,
                is_active,
                current_version,
                created_at,
                updated_at
            )
            VALUES
            (
                :page_key,
                :source_component_name,
                :owner_user_id,
                :report_title,
                :report_desc,
                'PRIVATE',
                TRUE,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING report_id
            """
        ),
        {
            "page_key": source["page_key"],
            "source_component_name": source["source_component_name"],
            "owner_user_id": str(current_user.id),
            "report_title": title,
            "report_desc": source["report_desc"],
        },
    )

    new_report_id = UUID(str(result.scalar_one()))

    await replace_report_definition(
        session,
        new_report_id,
        source_definition["columns"],
        source_definition["filters"],
        user_id=str(current_user.id),
    )

    await _create_report_version(
        session,
        new_report_id,
        str(current_user.id),
        f'Cloned from report {report_id}',
    )

    await session.commit()

    return {
        "report_id": str(new_report_id),
        "source_report_id": str(report_id),
        "report_title": title,
        "sharing_policy": "PRIVATE",
        "current_version": 1,
    }


@router.get("/{report_id}/users/lookup")
async def lookup_report_share_users(
    report_id: UUID,
    query: str = Query(min_length=2, max_length=120),
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    """Search active users who can be selected as report recipients."""
    report = await load_report(session, report_id)
    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_sharing")
    await require_report_edit_access(
        session,
        report,
        str(current_user.id),
    )

    result = await session.execute(
        text(
            """
            SELECT
                c_user_id,
                c_user_email,
                c_user_full_name
            FROM pulsar.t_user
            WHERE c_user_active IS TRUE
              AND c_user_id <> :current_user_id
              AND (
                    c_user_email ILIKE :search
                    OR c_user_full_name ILIKE :search
              )
            ORDER BY c_user_full_name NULLS LAST, c_user_email
            LIMIT 20
            """
        ),
        {
            "current_user_id": str(current_user.id),
            "search": "%" + query.strip() + "%",
        },
    )

    return [
        {
            "c_user_id": str(row["c_user_id"]),
            "c_user_email": row["c_user_email"],
            "c_user_full_name": row["c_user_full_name"],
        }
        for row in result.mappings().all()
    ]


@router.post("/{report_id}/shares")
async def share_report(
    report_id: UUID,
    payload: ReportShareInput,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_sharing")
    await require_report_edit_access(
        session,
        report,
        str(current_user.id),
    )

    if payload.target_user_id == current_user.id:
        raise HTTPException(
            status_code=422,
            detail="A report cannot be shared with its owner.",
        )

    await _load_target_user(
        session,
        payload.target_user_id,
    )

    await session.execute(
        text(
            """
            INSERT INTO pulsar.t_report_share
            (
                report_id,
                target_user_id,
                permission_level,
                shared_by,
                created_at,
                is_active
            )
            VALUES
            (
                :report_id,
                :target_user_id,
                :permission_level,
                :shared_by,
                CURRENT_TIMESTAMP,
                TRUE
            )
            ON CONFLICT (report_id, target_user_id)
            DO UPDATE SET
                permission_level = EXCLUDED.permission_level,
                shared_by = EXCLUDED.shared_by,
                created_at = CURRENT_TIMESTAMP,
                is_active = TRUE
            """
        ),
        {
            "report_id": str(report_id),
            "target_user_id": str(payload.target_user_id),
            "permission_level": payload.permission_level,
            "shared_by": str(current_user.id),
        },
    )

    if report["sharing_policy"] != "PUBLIC":
        await session.execute(
            text(
                """
                UPDATE pulsar.t_report
                SET
                    sharing_policy = 'SHARED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE report_id = :report_id
                """
            ),
            {"report_id": str(report_id)},
        )

    await session.commit()

    return {
        "report_id": str(report_id),
        "target_user_id": str(payload.target_user_id),
        "permission_level": payload.permission_level,
        "sharing_policy": (
            "PUBLIC"
            if report["sharing_policy"] == "PUBLIC"
            else "SHARED"
        ),
    }


@router.get("/{report_id}/shares")
async def list_report_shares(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)
    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_sharing")
    await require_report_edit_access(
        session,
        report,
        str(current_user.id),
    )

    result = await session.execute(
        text(
            """
            SELECT
                share.share_id,
                share.target_user_id,
                user_row.c_user_email,
                user_row.c_user_full_name,
                share.permission_level,
                share.shared_by,
                share.created_at,
                share.is_active
            FROM pulsar.t_report_share share
            INNER JOIN pulsar.t_user user_row
                ON user_row.c_user_id = share.target_user_id
            WHERE share.report_id = :report_id
            ORDER BY share.created_at DESC, share.target_user_id
            """
        ),
        {"report_id": str(report_id)},
    )

    return [
        {
            **dict(row),
            "share_id": str(row["share_id"]),
            "target_user_id": str(row["target_user_id"]),
            "shared_by": str(row["shared_by"]),
        }
        for row in result.mappings().all()
    ]


@router.delete("/{report_id}/shares/{target_user_id}")
async def unshare_report(
    report_id: UUID,
    target_user_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_sharing")
    await require_report_edit_access(
        session,
        report,
        str(current_user.id),
    )

    await session.execute(
        text(
            """
            UPDATE pulsar.t_report_share
            SET is_active = FALSE
            WHERE report_id = :report_id
              AND target_user_id = :target_user_id
              AND is_active IS TRUE
            """
        ),
        {
            "report_id": str(report_id),
            "target_user_id": str(target_user_id),
        },
    )

    remaining_result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_report_share
                WHERE report_id = :report_id
                  AND is_active IS TRUE
            )
            """
        ),
        {"report_id": str(report_id)},
    )

    if (
        not bool(remaining_result.scalar())
        and report["sharing_policy"] == "SHARED"
    ):
        await session.execute(
            text(
                """
                UPDATE pulsar.t_report
                SET
                    sharing_policy = 'PRIVATE',
                    updated_at = CURRENT_TIMESTAMP
                WHERE report_id = :report_id
                """
            ),
            {"report_id": str(report_id)},
        )

    await session.commit()

    return {
        "report_id": str(report_id),
        "target_user_id": str(target_user_id),
        "is_shared": False,
    }


@router.post("/{report_id}/publish")
async def publish_report(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_public")
    await require_permission(
        session,
        str(current_user.id),
        "PAGE.SUPERVISOR",
        report["page_key"],
    )
    await require_permission(
        session,
        str(current_user.id),
        "REPORT.PUBLIC.PUBLISH",
        report["page_key"],
    )

    await session.execute(
        text(
            """
            UPDATE pulsar.t_report
            SET
                sharing_policy = 'PUBLIC',
                updated_at = CURRENT_TIMESTAMP
            WHERE report_id = :report_id
            """
        ),
        {"report_id": str(report_id)},
    )

    await session.commit()

    return {
        "report_id": str(report_id),
        "sharing_policy": "PUBLIC",
    }


@router.post("/{report_id}/unpublish")
async def unpublish_report(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await _require_report_page_option(session, report["page_key"], "allow_public")
    await require_permission(
        session,
        str(current_user.id),
        "PAGE.SUPERVISOR",
        report["page_key"],
    )
    await require_permission(
        session,
        str(current_user.id),
        "REPORT.PUBLIC.PUBLISH",
        report["page_key"],
    )

    share_result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pulsar.t_report_share
                WHERE report_id = :report_id
                  AND is_active IS TRUE
            )
            """
        ),
        {"report_id": str(report_id)},
    )

    policy = "SHARED" if bool(share_result.scalar()) else "PRIVATE"

    await session.execute(
        text(
            """
            UPDATE pulsar.t_report
            SET
                sharing_policy = :sharing_policy,
                updated_at = CURRENT_TIMESTAMP
            WHERE report_id = :report_id
            """
        ),
        {
            "report_id": str(report_id),
            "sharing_policy": policy,
        },
    )

    await session.commit()

    return {
        "report_id": str(report_id),
        "sharing_policy": policy,
    }


@router.get("/{report_id}/versions")
async def list_report_versions(
    report_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )
    await require_report_view_access(
        session,
        report,
        str(current_user.id),
    )

    result = await session.execute(
        text(
            """
            SELECT
                version_id,
                version_no,
                changed_by,
                changed_at,
                change_note
            FROM pulsar.t_report_version
            WHERE report_id = :report_id
            ORDER BY version_no DESC
            """
        ),
        {"report_id": str(report_id)},
    )

    return [
        {
            **dict(row),
            "version_id": str(row["version_id"]),
            "changed_by": str(row["changed_by"]),
        }
        for row in result.mappings().all()
    ]


@router.post("/{report_id}/run")
async def run_report(
    report_id: UUID,
    payload: ReportRunInput,
    request: Request,
    current_user: UserProfileResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_audited_session),
):
    report = await load_report(session, report_id)

    await require_page_view_access(
        session,
        str(current_user.id),
        report["page_key"],
    )
    await require_report_view_access(
        session,
        report,
        str(current_user.id),
    )
    await validate_report_page(
        session,
        str(current_user.id),
        report["page_key"],
        report["source_component_name"],
    )

    definition = await load_report_definition(
        session,
        report_id,
    )

    return await execute_report(
        session,
        request,
        report,
        definition,
        user_id=str(current_user.id),
        profile_id=str(current_user.profile_id),
        selected_record=payload.selected_record,
        runtime_context=payload.runtime_context,
        limit=payload.limit,
        offset=payload.offset,
    )
