from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StateGraphInput:
    action: str
    params: dict[str, Any]
    source_node: str
    target_node: str


@dataclass(frozen=True)
class StateGraphCase:
    name: str
    before: dict[str, Any]
    input: StateGraphInput
    after: dict[str, Any]
    output: dict[str, Any]
    labels: tuple[str, ...]
    schema_version: str = "tla-testgraph.trace.v1"
    view: str = "external"
    layer: str = "external"
    controllability: str = "e2e_direct"
    generates: frozenset[str] = frozenset({"testgraph"})
    tags: tuple[str, ...] = ()
