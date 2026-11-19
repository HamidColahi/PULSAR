# ===============================================
# File: Pulsar/backend/ai_avatar/api_registry.py
#
# Description:
# Central registry and validation for internal PULSAR AI Avatar APIs
#
# Change Date: 2026-10-18
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from fastapi import APIRouter
from fastapi.routing import APIRoute


@dataclass(frozen=True, slots=True)
class APIEndpointDefinition:
    """Describe a stable internal API operation."""

    api_code: str
    http_method: str
    path: str
    handler_name: str
    description: str


_ENDPOINTS = (
    APIEndpointDefinition(
        api_code="AI_AVATAR_DEFAULT",
        http_method="GET",
        path="/ai-avatar/default",
        handler_name="get_default_avatar",
        description="Retrieve the default AI Avatar definition.",
    ),
    APIEndpointDefinition(
        api_code="AI_AVATAR_INTRODUCTION",
        http_method="POST",
        path="/ai-avatar/introduction",
        handler_name="get_avatar_introduction",
        description="Retrieve the authenticated user's Avatar introduction.",
    ),
    APIEndpointDefinition(
        api_code="AI_AVATAR_CHAT",
        http_method="POST",
        path="/ai-avatar/chat",
        handler_name="chat_with_avatar",
        description="Execute an authenticated AI Avatar chat request.",
    ),
)


def _build_registry(
    endpoints: tuple[APIEndpointDefinition, ...],
) -> Mapping[str, APIEndpointDefinition]:
    """Validate definitions and build an immutable API registry."""

    registry: dict[str, APIEndpointDefinition] = {}
    route_keys: set[tuple[str, str]] = set()

    for endpoint in endpoints:
        api_code = endpoint.api_code.strip()
        method = endpoint.http_method.strip().upper()
        path = endpoint.path.strip()
        handler_name = endpoint.handler_name.strip()

        if not api_code:
            raise ValueError("API code must not be empty.")

        if api_code in registry:
            raise ValueError(f"Duplicate API code: {api_code}")

        if not method:
            raise ValueError(
                f"HTTP method is required: {api_code}"
            )

        if not path.startswith("/") or path == "/":
            raise ValueError(f"Invalid API path: {api_code}")

        if not handler_name:
            raise ValueError(
                f"Handler name is required: {api_code}"
            )

        if not endpoint.description.strip():
            raise ValueError(
                f"Description is required: {api_code}"
            )

        route_key = (method, path)

        if route_key in route_keys:
            raise ValueError(
                f"Duplicate API route: {method} {path}"
            )

        route_keys.add(route_key)
        registry[api_code] = APIEndpointDefinition(
            api_code=api_code,
            http_method=method,
            path=path,
            handler_name=handler_name,
            description=endpoint.description.strip(),
        )

    return MappingProxyType(registry)


API_REGISTRY = _build_registry(_ENDPOINTS)


def get_api_definition(
    api_code: str,
) -> APIEndpointDefinition:
    """Return an API definition by its stable code."""

    try:
        return API_REGISTRY[api_code]
    except KeyError as exc:
        raise KeyError(
            f"Unknown internal API code: {api_code}"
        ) from exc


def validate_api_registry(router: APIRouter) -> None:
    """Ensure registered API definitions match the FastAPI router."""

    actual_routes: dict[tuple[str, str], list[APIRoute]] = {}

    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods or set():
            key = (method.upper(), route.path)
            actual_routes.setdefault(key, []).append(route)

    expected_routes: dict[tuple[str, str], APIEndpointDefinition] = {}

    for definition in API_REGISTRY.values():
        key = (
            definition.http_method,
            definition.path,
        )

        if key in expected_routes:
            raise RuntimeError(
                f"Duplicate API registry route: "
                f"{key[0]} {key[1]}"
            )

        expected_routes[key] = definition
        matches = actual_routes.get(key, [])

        if len(matches) != 1:
            raise RuntimeError(
                f"API registry mismatch for "
                f"'{definition.api_code}': expected exactly one "
                f"route for {key[0]} {key[1]}, "
                f"found {len(matches)}."
            )

        actual_handler = matches[0].endpoint.__name__

        if actual_handler != definition.handler_name:
            raise RuntimeError(
                f"API registry handler mismatch for "
                f"'{definition.api_code}': expected "
                f"'{definition.handler_name}', found "
                f"'{actual_handler}'."
            )

    for key, routes in actual_routes.items():
        if key not in expected_routes:
            handler_names = ", ".join(
                route.endpoint.__name__ for route in routes
            )
            raise RuntimeError(
                f"FastAPI route is missing from API registry: "
                f"{key[0]} {key[1]} "
                f"(handlers: {handler_names})."
            )