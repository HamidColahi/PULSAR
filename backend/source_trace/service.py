# ===============================================
# File: Pulsar/backend/source_trace/service.py
#
# Description:
# Application service for the PULSAR Static Source Topic Tracer
#
# Change Date: 2026-11-19 01:05
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import Iterable

from starlette.concurrency import run_in_threadpool

from tools.source_topic_trace import trace_source_topic

logger = logging.getLogger(__name__)


class SourceTraceService:
    """Execute static source tracing against the PULSAR repository."""

    def __init__(self, repository: str | Path | None = None) -> None:
        self.repository = (
            Path(repository).expanduser().resolve()
            if repository is not None
            else Path(__file__).resolve().parents[2]
        )

        if not self.repository.is_dir():
            raise NotADirectoryError(
                f"PULSAR repository directory not found: {self.repository}"
            )

    async def trace_topic(
        self,
        topic: str,
        max_nodes: int = 160,
        scope: Iterable[str] | None = None,
        relations: Iterable[str] | None = None,
        depth: int = 3,
    ) -> dict:
        """Run the synchronous tracing engine without blocking the event loop."""

        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Topic must not be empty.")

        if isinstance(max_nodes, bool) or not isinstance(max_nodes, int):
            raise ValueError("max_nodes must be an integer.")

        if isinstance(depth, bool) or not isinstance(depth, int):
            raise ValueError("depth must be an integer.")

        selected_scope = None if scope is None else tuple(scope)
        selected_relations = None if relations is None else tuple(relations)

        engine_call = partial(
            trace_source_topic,
            repository=self.repository,
            topic=topic.strip(),
            max_nodes=max_nodes,
            scope=selected_scope,
            relations=selected_relations,
            depth=depth,
        )

        try:
            result = await run_in_threadpool(engine_call)
        except (ValueError, NotADirectoryError):
            raise
        except Exception:
            logger.exception(
                "Unexpected Source Trace engine failure for topic '%s'.",
                topic,
            )
            raise

        if not isinstance(result, dict):
            raise RuntimeError(
                "Source Trace engine returned an invalid result."
            )

        required_sections = {
            "version",
            "options",
            "summary",
            "seeds",
            "files",
            "nodes",
            "edges",
            "limitations",
        }
        missing_sections = required_sections - result.keys()

        if missing_sections:
            raise RuntimeError(
                "Source Trace engine response is missing required sections: "
                f"{', '.join(sorted(missing_sections))}."
            )

        return result


source_trace_service = SourceTraceService()
