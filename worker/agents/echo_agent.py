from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_graph(config: dict | None = None):
    """Sample agent entrypoint used for bootstrap and smoke tests."""
    effective_config = config or {}

    def execute(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "received": payload,
            "config": effective_config,
            "executed_at": datetime.now(UTC).isoformat(),
        }

    return execute

