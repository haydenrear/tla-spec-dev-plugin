#!/usr/bin/env python3
"""Generate Python transition cases from a TLC DOT state graph dump.

This script is intentionally generic: it does not know product domains or
Python fake templates. It treats TLC as the case source of truth:

    TLC states and action-labeled edges -> Python case descriptors.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from . import case_modules
    from .corpus_diagnostics import enforce_case_cap
    from .extract_spec_manifest import load_manifest
    from .infer_action_params import UNCHECKED, ActionRecipe, CorpusMeasurement, build_recipes, build_recipes_from_path, infer_params, measure_recovery, render_audit, unchecked_param_names
    from .spec_paths import SpecTreePathError, is_relative_to, resolve_existing_from_cwd, resolve_existing_spec_input, resolve_spec_dir, resolve_spec_relative_path, resolve_spec_tree_out
except ImportError:  # pragma: no cover - direct script execution
    import case_modules  # type: ignore[no-redef]
    from corpus_diagnostics import enforce_case_cap
    from extract_spec_manifest import load_manifest
    from infer_action_params import UNCHECKED, ActionRecipe, CorpusMeasurement, build_recipes, build_recipes_from_path, infer_params, measure_recovery, render_audit, unchecked_param_names
    from spec_paths import SpecTreePathError, is_relative_to, resolve_existing_from_cwd, resolve_existing_spec_input, resolve_spec_dir, resolve_spec_relative_path, resolve_spec_tree_out


NODE_RE = re.compile(r'^\s*(-?\d+) \[label="(.*)"(?:,style = filled)?\];?$')
EDGE_RE = re.compile(r'^\s*(-?\d+) -> (-?\d+) \[label="([^"]+)"')
TRACE_SCHEMA_VERSION = "tla-testgraph.trace.v1"
VIEW_OUTPUT_DIRS = {"internal": "spec-unit", "external": "testgraph"}
VIEW_GENERATES = {"internal": "spec_unit", "external": "testgraph"}
DEFAULT_CONTROLLABILITY = {"internal": "unit_direct", "external": "e2e_direct"}
SUPPORTED_VIEWS = frozenset(VIEW_GENERATES)
SUPPORTED_CONTROLLABILITY = frozenset({"unit_direct", "e2e_direct", "environment", "observable", "hidden"})

#: Labels every negative case carries. An adapter selects the negative corpus
#: on ``NEGATIVE_LABEL`` and asserts refusal on ``REJECTED_LABEL``; both are
#: present so a consumer can tell "this case came from the negative pass" apart
#: from "this case expects a rejection", which need not always coincide.
NEGATIVE_LABEL = "negative"
REJECTED_LABEL = "expect:rejected"
NEGATIVE_MODES = ("off", "with-positive", "only")
NEGATIVE_DEDUPE_MODES = ("none", "guard-reads")


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    action: str


@dataclass(frozen=True)
class ActionMetadata:
    name: str
    layer: str
    controllability: str
    generates: tuple[str, ...]
    tags: tuple[str, ...] = ()
    #: `expected_zero: "<why>"` in actions.yml. A DECLARED zero-case action --
    #: the reason is required and is printed, so a hole reads as stated rather
    #: than silent. An UNDECLARED zero is a failure; see `report_coverage`.
    expected_zero: str | None = None


@dataclass(frozen=True)
class PreparedCase:
    name: str
    edge: Edge
    before: dict[str, Any]
    after: dict[str, Any]
    params: dict[str, Any]
    output_value: Any
    output_expression: str
    changes: dict[str, dict[str, Any]]
    labels: tuple[str, ...]
    metadata: ActionMetadata


def run_tlc_dump(
    tla_path: Path,
    cfg_path: Path,
    dot_path: Path,
    tlc2: str,
    search_path: "case_modules.ModuleSearchPath | None" = None,
) -> None:
    """Explore ``tla_path`` with TLC and dump the state graph.

    EV-02-DF-02: TLC runs with cwd = the ``.tla``'s directory and resolves
    ``EXTENDS`` against that directory and the ``TLA-Library`` search path --
    never against the current directory. A module that extends a view in another
    directory therefore needs the view's directory on that path, which
    ``search_path`` supplies. Without it the failure is a
    ``tla2sany.semantic.AbortException`` and a ``CalledProcessError`` traceback,
    which is why the caller resolves the hierarchy BEFORE getting here.
    """
    dot_path.parent.mkdir(parents=True, exist_ok=True)
    spec_dir = tla_path.parent.resolve()
    metadir = dot_path.parent / ".tlc-states" / tla_path.stem
    command = [
        tlc2,
        "-cleanup",
        "-deadlock",
        "-fp",
        "1",
        "-metadir",
        str(metadir.resolve()),
        "-config",
        str(cfg_path.resolve()),
        "-dump",
        "dot,actionlabels",
        str(dot_path.resolve()),
        str(tla_path.resolve()),
    ]
    env = case_modules.tlc_environment(search_path)
    try:
        subprocess.run(command, check=True, cwd=spec_dir, env=env)
    except subprocess.CalledProcessError as error:
        lines = [
            f"ERROR: TLC exited {error.returncode} exploring {tla_path.name} "
            f"(config {cfg_path.name}).",
            f"  working directory: {spec_dir}",
        ]
        if search_path is not None and not search_path.is_self_contained:
            lines.append(
                "  module search path (TLA-Library): "
                + ", ".join(str(directory) for directory in search_path.directories)
            )
            lines.append(f"  EXTENDS resolved elsewhere: {search_path.describe()}")
        else:
            lines.append(
                "  module search path: the spec directory only -- every EXTENDS "
                "resolved beside the module."
            )
        lines.append(
            "  TLC's own message is above. It is not a case-generation failure: "
            "nothing was written."
        )
        raise SystemExit("\n".join(lines)) from error
    finally:
        shutil.rmtree(metadir, ignore_errors=True)


def load_dot(path: Path) -> tuple[dict[str, dict[str, Any]], list[Edge]]:
    states: dict[str, dict[str, Any]] = {}
    edges: list[Edge] = []
    for line in path.read_text().splitlines():
        node_match = NODE_RE.match(line)
        if node_match:
            node_id, raw_label = node_match.groups()
            states[node_id] = parse_state_label(raw_label)
            continue
        edge_match = EDGE_RE.match(line)
        if edge_match:
            source, target, action = edge_match.groups()
            edges.append(Edge(source=source, target=target, action=action))
    return states, edges


def parse_state_label(raw_label: str) -> dict[str, Any]:
    state: dict[str, Any] = {}
    raw_label = raw_label.replace(r"\"", '"')
    current: tuple[str, str] | None = None
    for raw_part in raw_label.split(r"\n"):
        part = raw_part.strip()
        while part.startswith(("/", "\\")):
            part = part[1:].strip()
        if " = " not in part:
            if current is not None and part:
                current = (current[0], f"{current[1]} {part}")
            continue
        if current is not None:
            state[current[0]] = parse_tlc_value(current[1].strip())
        name, value = part.split(" = ", 1)
        current = (name.strip(), value.strip())
    if current is not None:
        state[current[0]] = parse_tlc_value(current[1].strip())
    return state


def parse_tlc_value(value: str) -> Any:
    if value == "{}":
        return frozenset()
    if value.startswith("{") and value.endswith("}"):
        body = value[1:-1].strip()
        if not body:
            return frozenset()
        return frozenset(freeze_set_member(parse_tlc_value(part.strip())) for part in split_top_level(body, ","))
    if value.startswith("[") and value.endswith("]") and "|->" in value:
        return parse_tlc_record(value)
    if value.startswith("(") and value.endswith(")") and ":>" in value:
        return parse_tlc_function(value)
    if value.startswith("<<") and value.endswith(">>"):
        body = value[2:-2].strip()
        if not body:
            return ()
        return tuple(parse_tlc_value(part.strip()) for part in split_top_level(body, ","))
    return parse_atom(value)


def parse_tlc_function(value: str) -> dict[str, Any]:
    body = value[1:-1].strip()
    result: dict[str, Any] = {}
    for part in split_top_level(body, "@@"):
        split = split_top_level_once(part, ":>")
        if split is None:
            continue
        key, raw_value = split
        result[str(parse_atom(key.strip()))] = parse_tlc_value(raw_value.strip())
    return result


def parse_tlc_record(value: str) -> dict[str, Any]:
    body = value[1:-1].strip()
    result: dict[str, Any] = {}
    if not body:
        return result
    for part in split_top_level(body, ","):
        split = split_top_level_once(part, "|->")
        if split is None:
            continue
        key, raw_value = split
        result[str(parse_atom(key.strip()))] = parse_tlc_value(raw_value.strip())
    return result


def freeze_set_member(value: Any) -> Any:
    if isinstance(value, dict):
        return frozenset((key, freeze_set_member(inner)) for key, inner in value.items())
    if isinstance(value, list):
        return tuple(freeze_set_member(inner) for inner in value)
    if isinstance(value, tuple):
        return tuple(freeze_set_member(inner) for inner in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_set_member(inner) for inner in value)
    return value


def split_top_level_once(value: str, separator: str) -> tuple[str, str] | None:
    parts = split_top_level(value, separator, maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def split_top_level(value: str, separator: str, maxsplit: int = -1) -> list[str]:
    parts: list[str] = []
    start = 0
    index = 0
    splits = 0
    stack: list[str] = []
    in_string = False
    while index < len(value):
        if in_string:
            if value[index] == '"' and not is_escaped(value, index):
                in_string = False
            index += 1
            continue

        if value[index] == '"':
            in_string = True
            index += 1
            continue

        if value.startswith("<<", index):
            stack.append(">>")
            index += 2
            continue

        if stack and value.startswith(stack[-1], index):
            index += len(stack.pop())
            continue

        if value[index] in "({[":
            stack.append({"(": ")", "{": "}", "[": "]"}[value[index]])
            index += 1
            continue

        if stack and value[index] == stack[-1]:
            stack.pop()
            index += 1
            continue

        if not stack and value.startswith(separator, index) and (maxsplit < 0 or splits < maxsplit):
            parts.append(value[start:index].strip())
            index += len(separator)
            start = index
            splits += 1
            continue

        index += 1

    parts.append(value[start:].strip())
    return parts


def is_escaped(value: str, index: int) -> bool:
    slash_count = 0
    cursor = index - 1
    while cursor >= 0 and value[cursor] == "\\":
        slash_count += 1
        cursor -= 1
    return slash_count % 2 == 1


def parse_atom(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def normalize_string_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(str(item) for item in value)
    raise ValueError(f"expected string or list of strings, got {value!r}")


class ZeroCaseActionError(RuntimeError):
    """A declared view action generated no cases and did not declare that zero.

    Deliberately an ERROR and not a warning. The warning form shipped, was
    printed, and was not read -- the corpus meant to decide a goal did not
    contain the case for the action the goal names, and it was found only
    because somebody opened `case_coverage.json` by hand.
    """

    def __init__(self, view: str, actions: list[str], record_path: Any) -> None:
        self.view = view
        self.actions = list(actions)
        self.record_path = record_path
        super().__init__(
            f"{len(actions)} declared {view} action(s) generated ZERO cases without "
            f"an `expected_zero` declaration: {', '.join(actions)}. "
            f"Coverage record written to {record_path}."
        )


def default_action_metadata(action: str, view: str) -> ActionMetadata:
    return ActionMetadata(
        name=action,
        layer=view,
        controllability=DEFAULT_CONTROLLABILITY[view],
        generates=(VIEW_GENERATES[view],),
    )


def load_action_metadata(path: Path | None, spec_dir: Path | None = None) -> dict[str, ActionMetadata]:
    if path is None:
        return {}
    metadata_path = resolve_existing_spec_input(path, spec_dir) if spec_dir is not None else resolve_existing_from_cwd(path)
    loaded = load_manifest(metadata_path)
    raw_actions = loaded.get("actions", loaded)
    if not isinstance(raw_actions, dict):
        raise ValueError(f"action metadata root must be a mapping: {metadata_path}")

    metadata: dict[str, ActionMetadata] = {}
    for action, raw_spec in raw_actions.items():
        if raw_spec is None:
            raw_spec = {}
        if not isinstance(raw_spec, dict):
            raise ValueError(f"action metadata for {action} must be a mapping")
        layer = str(raw_spec.get("layer", "internal"))
        if layer not in SUPPORTED_VIEWS:
            raise ValueError(f"unsupported layer for {action}: {layer}")
        controllability = str(raw_spec.get("controllability", DEFAULT_CONTROLLABILITY[layer]))
        if controllability not in SUPPORTED_CONTROLLABILITY:
            raise ValueError(f"unsupported controllability for {action}: {controllability}")
        metadata[str(action)] = ActionMetadata(
            name=str(action),
            layer=layer,
            controllability=controllability,
            generates=normalize_string_list(raw_spec.get("generates", (VIEW_GENERATES[layer],))),
            tags=normalize_string_list(raw_spec.get("tags", ())),
            expected_zero=_expected_zero(action, raw_spec.get("expected_zero")),
        )
    return metadata


def _expected_zero(action: str, raw: Any) -> str | None:
    """`expected_zero` must carry a REASON. A bare true declares nothing.

    The whole value of a declared zero is that a reader can tell "known-inert
    until MH-03 lands" from "your wrapper is broken and your goal is
    unverified". A boolean cannot carry that, so a boolean is refused.
    """
    if raw is None:
        return None
    if isinstance(raw, bool) or not str(raw).strip():
        raise ValueError(
            f"expected_zero for {action} must be a REASON string, not {raw!r}. "
            "Write why the action generates no cases -- e.g. "
            '\'guard unsatisfiable until MH-03 lands\' -- so a reader can tell a '
            "known-inert action from a broken one."
        )
    return str(raw).strip()


def action_metadata_for(action: str, view: str, metadata: dict[str, ActionMetadata]) -> ActionMetadata:
    return metadata.get(action) or default_action_metadata(action, view)


def should_emit_action(action_metadata: ActionMetadata, view: str) -> bool:
    return action_metadata.layer == view and VIEW_GENERATES[view] in set(action_metadata.generates)


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = sorted(set(before) | set(after))
    return {
        field: {"before": before.get(field), "after": after.get(field)}
        for field in fields
        if before.get(field) != after.get(field)
    }


def to_plain_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_plain_value(inner) for key, inner in sorted(value.items(), key=lambda item: repr(item[0]))}
    if isinstance(value, tuple):
        return [to_plain_value(inner) for inner in value]
    if isinstance(value, (set, frozenset)):
        return [to_plain_value(inner) for inner in sorted(value, key=repr)]
    return value


def freeze_for_signature(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((str(key), freeze_for_signature(inner)) for key, inner in sorted(value.items(), key=lambda item: repr(item[0])))
    if isinstance(value, (list, tuple)):
        return tuple(freeze_for_signature(inner) for inner in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((freeze_for_signature(inner) for inner in value), key=repr))
    return value


def params_from_action_marker(edge: Edge, after: dict[str, Any], view: str) -> dict[str, Any]:
    marker_name = "lastExternalAction" if view == "external" else "lastInternalAction"
    marker = after.get(marker_name)
    if not isinstance(marker, dict) or marker.get("name") != edge.action:
        return {}
    params = marker.get("params", {})
    if params in (None, (), [], frozenset()):
        return {}
    if not isinstance(params, dict):
        return {}
    return dict(to_plain_value(params))


def declared_param_names(body: str, params: tuple[str, ...], view: str) -> dict[str, str]:
    """Map each formal parameter to the argument name its own module declares.

    ``params_from_action_marker`` reads exactly these names out of a dump's
    after-state, which is why every positive case -- and every adapter written
    against one -- is keyed by them. A case with no transition to read them from
    had no way to reach the same declaration, so `CA-06-DF-02` left the negative
    corpus emitting the FORMAL names and all 11 cases it produces for
    ``examples/distributed_history`` died on ``KeyError`` before asserting
    anything. The declaration is in the module either way; this reads it from
    the source instead of from a state pair.

    Only a marker field whose value is a bare formal parameter is a rename: an
    expression is not a parameter. A formal the marker does not mention keeps
    its own name, because dropping it would lose an argument the guard was
    evaluated on. A module that declares no action marker gets an empty map --
    which is why nothing moves for ``QuotaLedger``, whose sealed kill tables
    this repository quotes throughout.

    THE COLLISION GUARD BELOW IS NARROWER THAN IT LOOKS, and this paragraph
    replaces one that stated an invariant the code does not enforce
    (`CA-07-DF-07`, from the independent review of PR #269). It refuses only
    when two RENAMED formals land on one declared name. A rename that collides
    with the name of a formal the marker DOES NOT mention still passes:
    ``Foo(x, y)`` with ``params |-> [y |-> x]`` maps ``x -> y`` while ``y``
    keeps ``y``, so the emitted dict has ONE key and SILENTLY DROPS AN
    ARGUMENT, and the cross-check above then hits the same `continue` vacuity
    in narrower form. No module in this repository is shaped that way, and the
    case is named rather than repaired here.
    """
    marker = "lastExternalAction" if view == "external" else "lastInternalAction"
    anchor = re.search(rf"\b{marker}'\s*=\s*\[", body)
    if anchor is None:
        return {}
    opener = re.search(r"\bparams\s*\|->\s*\[", body[anchor.end() :])
    if opener is None:
        return {}
    start = anchor.end() + opener.end()
    depth, end = 1, start
    while end < len(body) and depth:
        depth += {"[": 1, "]": -1}.get(body[end], 0)
        end += 1
    fields: list[str] = []
    field = ""
    depth = 0
    for char in body[start : end - 1]:
        depth += {"[": 1, "(": 1, "{": 1, "]": -1, ")": -1, "}": -1}.get(char, 0)
        if char == "," and depth == 0:
            fields.append(field)
            field = ""
        else:
            field += char
    fields.append(field)
    names: dict[str, str] = {}
    for field in fields:
        match = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*\|->\s*([A-Za-z_]\w*)\s*", field)
        if match and match.group(2) in params:
            names[match.group(2)] = match.group(1)
    return names if len(set(names.values())) == len(names) else {}


def params_for_case(
    edge: Edge,
    raw_before: dict[str, Any],
    raw_after: dict[str, Any],
    view: str,
    param_recipes: dict[str, ActionRecipe] | None,
) -> dict[str, Any]:
    """Determine an edge's action arguments.

    An explicit action marker in the model wins when one exists -- a model that
    states its own arguments is authoritative. Otherwise MF-029 recovers them
    from the case's own before/after pair. Recovery derives from the BEFORE
    state and the transition; where it cannot, the parameter is ``UNCHECKED``
    rather than a fabricated value that would make a comparison succeed.
    """
    declared = params_from_action_marker(edge, raw_after, view)
    if declared:
        return declared
    return infer_params(edge.action, raw_before, raw_after, param_recipes)


def param_provenance_labels(params: dict[str, Any]) -> list[str]:
    """Labels recording how trustworthy an emitted case's arguments are.

    These exist so an unrecoverable parameter is MARKED AND KEPT. No case is
    ever dropped, filtered, or skipped for failing recovery -- the corpus is
    complete either way, and the label is how a consumer tells the difference.
    """
    if not params:
        return []
    unchecked = unchecked_param_names(params)
    if not unchecked:
        return ["params:recovered"]
    labels = ["params:unchecked"]
    labels.extend(f"params:unchecked:{name}" for name in unchecked)
    if len(unchecked) < len(params):
        labels.append("params:partial")
    return labels


def case_name(index: int, action: str) -> str:
    snake = re.sub(r"(?<!^)([A-Z])", r"_\1", action).lower()
    snake = re.sub(r"[^a-z0-9_]+", "_", snake).strip("_")
    return f"case_{index:04d}_{snake}"


def py_repr(value: Any) -> str:
    if value is UNCHECKED:
        # Rendered as the imported sentinel, never as a literal. A generated
        # case must not be able to state an argument it does not know.
        return "UNCHECKED"
    if isinstance(value, frozenset):
        if not value:
            return "frozenset()"
        items = ", ".join(py_repr(item) for item in sorted(value, key=repr))
        return f"frozenset([{items}])"
    if isinstance(value, tuple):
        items = ", ".join(py_repr(item) for item in value)
        if len(value) == 1:
            items += ","
        return f"({items})"
    if isinstance(value, dict):
        items = ", ".join(f"{key!r}: {py_repr(inner)}" for key, inner in sorted(value.items(), key=lambda item: repr(item[0])))
        return "{" + items + "}"
    return repr(value)


def load_object(path: str) -> Any:
    """Resolve ``module:object`` or ``path/to/file.py:object``.

    BS-07 (#166): a ticket workspace is ``specs/tickets/<ID>/desired`` and
    ticket ids carry dashes (``MH-42``), so a ticket's OWN ``tlc_projection.py``
    has no dotted module name. Naming ``specs.current.tlc_projection`` instead
    silently generates the ticket corpus with the PROJECT projector. A module
    half ending in ``.py`` is therefore loaded from that file, under a private
    module name, so no other importable ``tlc_projection`` can shadow it.
    """
    module_name, sep, object_name = path.rpartition(":")
    if not sep or not module_name or not object_name:
        raise ValueError(
            f"object path must be module:object or path/to/file.py:object, got {path!r}"
        )
    if module_name.endswith(".py"):
        module = _load_module_file(Path(module_name))
    else:
        module = importlib.import_module(module_name)
    obj: Any = module
    for part in object_name.split("."):
        obj = getattr(obj, part)
    return obj


def _load_module_file(file: Path) -> Any:
    import hashlib
    import importlib.util

    file = file.resolve()
    if not file.is_file():
        raise ValueError(f"projector file not found: {file}")
    digest = hashlib.sha256(str(file).encode("utf-8")).hexdigest()[:16]
    name = f"_tla_spec_dev_projector_{file.stem}_{digest}"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load projector file {file}")
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: a dataclass in the projector looks its own
    # module up in sys.modules while the class body runs.
    sys.modules[name] = module
    # The file's own directory leads sys.path while it executes, so a sibling
    # helper it imports resolves next to it rather than elsewhere.
    parent = str(file.parent)
    sys.path.insert(0, parent)
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        try:
            sys.path.remove(parent)
        except ValueError:
            pass
    return module


def labels_for_case(
    *,
    before: dict[str, Any],
    action: str,
    after: dict[str, Any],
    changes: dict[str, dict[str, Any]],
    labelers: list[Any],
) -> list[str]:
    labels = [action]
    for labeler in labelers:
        try:
            produced = labeler(before=before, action=action, after=after, changed=changes)
        except TypeError as exc:
            if "keyword" not in str(exc) and "argument" not in str(exc):
                raise
            produced = labeler(before, action, after, changes)
        if isinstance(produced, str):
            produced = [produced]
        if produced is None:
            continue
        for label in produced:
            rendered = str(label)
            if rendered and rendered not in labels:
                labels.append(rendered)
    return labels


def call_state_projector(projector: Any | None, state: dict[str, Any]) -> dict[str, Any]:
    if projector is None:
        return state
    try:
        projected = projector(state=state)
    except TypeError as exc:
        if "keyword" not in str(exc) and "argument" not in str(exc):
            raise
        projected = projector(state)
    if not isinstance(projected, dict):
        raise TypeError(f"state projector must return a dict, got {type(projected).__name__}")
    return projected


def call_output_projector(
    projector: Any | None,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    projected_before: dict[str, Any],
    projected_after: dict[str, Any],
    action: str,
    params: dict[str, Any],
    changed: dict[str, dict[str, Any]],
    view: str,
) -> tuple[Any, str]:
    if projector is None:
        return changed, f"StateGraphOutput(changed={py_repr(changed)})"
    try:
        output = projector(
            before=before,
            after=after,
            projected_before=projected_before,
            projected_after=projected_after,
            action=action,
            params=params,
            changed=changed,
            view=view,
        )
    except TypeError as exc:
        if "keyword" not in str(exc) and "argument" not in str(exc):
            raise
        output = projector(before, action, after, params)
    return output, py_repr(output)


def prepare_cases(
    *,
    states: dict[str, dict[str, Any]],
    edges: list[Edge],
    view: str,
    action_metadata: dict[str, ActionMetadata],
    labelers: list[Any],
    state_projector: Any | None,
    output_projector: Any | None,
    dedupe: str,
    param_recipes: dict[str, ActionRecipe] | None = None,
) -> list[PreparedCase]:
    prepared: list[PreparedCase] = []
    seen: set[Any] = set()
    for edge in edges:
        raw_before = states[edge.source]
        raw_after = states[edge.target]
        before = call_state_projector(state_projector, raw_before)
        after = call_state_projector(state_projector, raw_after)
        # MF-029: recovery reads the RAW states, not the projected ones. A
        # projector may drop or rename fields, and a parameter recovered from a
        # projection would be recovered from something other than the model.
        params = params_for_case(edge, raw_before, raw_after, view, param_recipes)
        changes = changed_fields(before, after)
        output_value, output_expression = call_output_projector(
            output_projector,
            before=raw_before,
            after=raw_after,
            projected_before=before,
            projected_after=after,
            action=edge.action,
            params=params,
            changed=changes,
            view=view,
        )
        if dedupe == "projected":
            signature = freeze_for_signature(
                {
                    "action": edge.action,
                    "params": params,
                    "before": before,
                    "after": after,
                    "output": output_value,
                }
            )
            if signature in seen:
                continue
            seen.add(signature)
        labels = labels_for_case(before=before, action=edge.action, after=after, changes=changes, labelers=labelers)
        for provenance in param_provenance_labels(params):
            if provenance not in labels:
                labels.append(provenance)
        metadata = action_metadata_for(edge.action, view, action_metadata)
        prepared.append(
            PreparedCase(
                name=case_name(len(prepared) + 1, edge.action),
                edge=edge,
                before=before,
                after=after,
                params=params,
                output_value=output_value,
                output_expression=output_expression,
                changes=changes,
                labels=tuple(labels),
                metadata=metadata,
            )
        )
    return prepared


def render_python_package(
    *,
    module: str,
    states: dict[str, dict[str, Any]],
    edges: list[Edge],
    package_dir: Path,
    view: str = "internal",
    action_metadata: dict[str, ActionMetadata] | None = None,
    labelers: list[Any] | None = None,
    state_projector: Any | None = None,
    output_projector: Any | None = None,
    dedupe: str = "none",
    param_recipes: dict[str, ActionRecipe] | None = None,
    negative: str = "off",
    negative_dedupe: str = "guard-reads",
    negative_actions: tuple[str, ...] = (),
    tla_source: str | None = None,
    cfg_text: str | None = None,
    projector_description: str = "none",
    negative_report_out: "list[NegativeCorpusReport] | None" = None,
    ports: str = "off",
    port_dedupe: str = "region",
    port_catalog: "PortCatalog | None" = None,
    port_report_out: "list[PortCorpusReport] | None" = None,
) -> list[PreparedCase]:
    """Write the generated package and return its cases.

    The return type is deliberately unchanged from before HP-03 -- twelve call
    sites read it as a list. The negative pass reports through
    ``negative_report_out``, which the caller appends to, so adding a mode did
    not force an unrelated signature change on every existing consumer.
    """
    metadata = action_metadata or {}
    emitted_edges = [
        edge
        for edge in edges
        if should_emit_action(action_metadata_for(edge.action, view, metadata), view)
    ]
    if negative == "only":
        prepared_cases: list[PreparedCase] = []
    else:
        prepared_cases = prepare_cases(
            states=states,
            edges=emitted_edges,
            view=view,
            action_metadata=metadata,
            labelers=labelers or [],
            state_projector=state_projector,
            output_projector=output_projector,
            dedupe=dedupe,
            param_recipes=param_recipes,
        )
    negative_report: NegativeCorpusReport | None = None
    if negative != "off":
        if tla_source is None or cfg_text is None:
            raise ValueError("negative generation needs the module and config text")
        negative_cases, negative_report = negative_cases_for_corpus(
            states=states,
            edges=edges,
            tla_source=tla_source,
            cfg_text=cfg_text,
            view=view,
            action_metadata=metadata,
            state_projector=state_projector,
            dedupe=negative_dedupe,
            only_actions=negative_actions,
            param_recipes=param_recipes,
            start_index=len(prepared_cases) + 1,
        )
        prepared_cases = prepared_cases + negative_cases
        if negative_report_out is not None:
            negative_report_out.append(negative_report)
    port_report: PortCorpusReport | None = None
    if ports != "off":
        if tla_source is None or cfg_text is None:
            raise ValueError("port generation needs the module and config text")
        catalog = port_catalog if port_catalog is not None else PortCatalog((), {}, "(none)")
        regions, skipped = port_regions(
            catalog,
            *_signatures_for_regions(tla_source, cfg_text),
        )
        port_cases, port_report = port_cases_for_corpus(
            source_cases=prepared_cases,
            catalog=catalog,
            regions=regions,
            skipped=skipped,
            dedupe=port_dedupe,
            start_index=(1 if ports == "only" else len(prepared_cases) + 1),
        )
        port_report.mode = ports
        port_report.manifest = catalog.source
        prepared_cases = port_cases if ports == "only" else prepared_cases + port_cases
        if port_report_out is not None:
            port_report_out.append(port_report)
    package_dir.mkdir(parents=True, exist_ok=True)
    write(package_dir / "__init__.py", render_init())
    write(package_dir / "types.py", render_types())
    write(package_dir / "cases.py", render_cases(module, states, prepared_cases, view))
    write(package_dir / "doubles.py", render_doubles())
    write(package_dir / "validators.py", render_validators())
    write(
        package_dir / "docs.md",
        render_docs(
            module,
            view,
            len(states),
            len(prepared_cases),
            len(emitted_edges),
            len(edges),
            dedupe,
            negative=negative,
            negative_report=negative_report,
            projector_description=projector_description,
            ports=ports,
            port_report=port_report,
        ),
    )
    # Every prepared case has now been written. The caller gates the corpus
    # AFTER this point, so a failing cap gate never removes anything -- the
    # package on disk is complete either way (MF-014).
    return prepared_cases


def render_init() -> str:
    return (
        "from .cases import CASES, CASES_BY_NAME, SOURCE_MODULE, SOURCE_VIEW\n"
        "from .doubles import ScriptedTransitionDouble\n"
        "from .types import UNCHECKED, StateGraphCase, StateGraphInput, StateGraphOutput, StateGraphRejection\n"
        "from .validators import assert_case_replays, assert_rejection_is_inert\n\n"
        "__all__ = [\n"
        "    \"CASES\",\n"
        "    \"CASES_BY_NAME\",\n"
        "    \"SOURCE_MODULE\",\n"
        "    \"SOURCE_VIEW\",\n"
        "    \"UNCHECKED\",\n"
        "    \"ScriptedTransitionDouble\",\n"
        "    \"StateGraphCase\",\n"
        "    \"StateGraphInput\",\n"
        "    \"StateGraphOutput\",\n"
        "    \"StateGraphRejection\",\n"
        "    \"assert_case_replays\",\n"
        "    \"assert_rejection_is_inert\",\n"
        "]\n"
    )


def render_types() -> str:
    return (
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n"
        "from dataclasses import field\n"
        "from typing import Any\n\n\n"
        "class Unchecked:\n"
        "    \"\"\"An action argument this corpus could not recover from the state pair.\n\n"
        "    MF-029. It is NOT None, \"\" or 0 -- those are values a model could\n"
        "    legitimately produce, so an adapter comparing against one could pass by\n"
        "    coincidence. UNCHECKED equals only itself, so any check expecting a\n"
        "    concrete argument fails against it instead of passing vacuously.\n\n"
        "    A case carrying UNCHECKED is still a real case and is never dropped: the\n"
        "    sentinel marks the argument, it does not disqualify the transition.\n"
        "    \"\"\"\n\n"
        "    _instance = None\n\n"
        "    def __new__(cls):\n"
        "        if cls._instance is None:\n"
        "            cls._instance = super().__new__(cls)\n"
        "        return cls._instance\n\n"
        "    def __repr__(self) -> str:\n"
        "        return \"UNCHECKED\"\n\n"
        "    def __bool__(self) -> bool:\n"
        "        return False\n\n"
        "    def __eq__(self, other: Any) -> bool:\n"
        "        return other is self\n\n"
        "    def __ne__(self, other: Any) -> bool:\n"
        "        return other is not self\n\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(\"tla-spec-dev.UNCHECKED\")\n\n\n"
        "UNCHECKED = Unchecked()\n\n\n"
        "@dataclass(frozen=True)\n"
        "class StateGraphInput:\n"
        "    action: str\n"
        "    source_node: str\n"
        "    target_node: str\n"
        "    params: dict[str, Any] = field(default_factory=dict)\n\n\n"
        "@dataclass(frozen=True)\n"
        "class ActionMetadata:\n"
        "    layer: str = \"internal\"\n"
        "    controllability: str = \"unit_direct\"\n"
        "    generates: frozenset[str] = frozenset((\"spec_unit\",))\n"
        "    tags: frozenset[str] = frozenset()\n\n\n"
        "@dataclass(frozen=True)\n"
        "class StateGraphOutput:\n"
        "    changed: dict[str, dict[str, Any]]\n\n\n"
        "@dataclass(frozen=True)\n"
        "class StateGraphRejection:\n"
        "    \"\"\"The expected outcome of a call the model does not enable (HP-03).\n\n"
        "    Emitted by the negative corpus: at this before-state the action's own\n"
        "    body evaluates to a definite FALSE, so the program must REFUSE the\n"
        "    call. ``reason`` is the violated conjunct copied verbatim out of the\n"
        "    module -- it is the model's words, not a classification invented here,\n"
        "    so an adapter comparing rejection reasons is comparing against the\n"
        "    specification rather than against this generator.\n\n"
        "    ``changed`` is always empty and is spelled out rather than implied: a\n"
        "    refused call changes no modeled variable, which is the second half of\n"
        "    the assertion and the half a status-only oracle would miss.\n"
        "    \"\"\"\n\n"
        "    action: str\n"
        "    params: dict[str, Any]\n"
        "    reason: str\n"
        "    changed: dict[str, dict[str, Any]] = field(default_factory=dict)\n"
        "    #: Variables that record the OUTCOME of a call rather than the state it\n"
        "    #: left behind, derived from the model: the write set of every action\n"
        "    #: this module uses to spell a refusal out. A real program's refusal\n"
        "    #: does change these -- it reports that it refused -- so an adapter must\n"
        "    #: report them unobservable, and `after == before` is asserted over\n"
        "    #: everything else. When a model declares no refusal actions this tuple\n"
        "    #: is empty and full inertness is asserted.\n"
        "    outcome_fields: tuple[str, ...] = ()\n\n\n"
        "@dataclass(frozen=True)\n"
        "class StateGraphCase:\n"
        "    name: str\n"
        "    before: dict[str, Any]\n"
        "    input: StateGraphInput\n"
        "    output: Any\n"
        "    after: dict[str, Any]\n"
        "    labels: frozenset[str]\n"
        f"    schema_version: str = {TRACE_SCHEMA_VERSION!r}\n"
        "    view: str = \"internal\"\n"
        "    layer: str = \"internal\"\n"
        "    controllability: str = \"unit_direct\"\n"
        "    generates: frozenset[str] = frozenset((\"spec_unit\",))\n"
        "    tags: frozenset[str] = frozenset()\n"
        "    metadata: ActionMetadata = field(default_factory=ActionMetadata)\n"
    )


def render_cases(
    module: str,
    states: dict[str, dict[str, Any]],
    cases: list[PreparedCase],
    view: str,
) -> str:
    lines = [
        "from __future__ import annotations\n\n",
        "from .types import UNCHECKED, ActionMetadata, StateGraphCase, StateGraphInput, StateGraphOutput, StateGraphRejection\n\n\n",
        f'SCHEMA_VERSION = {TRACE_SCHEMA_VERSION!r}\n',
        f'SOURCE_MODULE = {module!r}\n',
        f'SOURCE_VIEW = {view!r}\n',
        f"STATE_COUNT = {len(states)}\n",
        f"TRANSITION_COUNT = {len(cases)}\n\n",
        "CASES = [\n",
    ]
    for case in cases:
        edge = case.edge
        metadata = case.metadata
        lines.extend(
            [
                "    StateGraphCase(\n",
                f"        name={case.name!r},\n",
                f"        before={py_repr(case.before)},\n",
                "        input=StateGraphInput(\n",
                f"            action={edge.action!r},\n",
                f"            source_node={edge.source!r},\n",
                f"            target_node={edge.target!r},\n",
                f"            params={py_repr(case.params)},\n",
                "        ),\n",
                f"        output={case.output_expression},\n",
                f"        after={py_repr(case.after)},\n",
                f"        labels=frozenset({py_repr(case.labels)}),\n",
                "        schema_version=SCHEMA_VERSION,\n",
                "        view=SOURCE_VIEW,\n",
                f"        layer={metadata.layer!r},\n",
                f"        controllability={metadata.controllability!r},\n",
                f"        generates=frozenset({py_repr(metadata.generates)}),\n",
                f"        tags=frozenset({py_repr(metadata.tags)}),\n",
                "        metadata=ActionMetadata(\n",
                f"            layer={metadata.layer!r},\n",
                f"            controllability={metadata.controllability!r},\n",
                f"            generates=frozenset({py_repr(metadata.generates)}),\n",
                f"            tags=frozenset({py_repr(metadata.tags)}),\n",
                "        ),\n",
                "    ),\n",
            ]
        )
    lines.extend(["]\n\n", "CASES_BY_NAME = {case.name: case for case in CASES}\n"])
    return "".join(lines)


def render_doubles() -> str:
    return (
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "from .types import StateGraphCase, StateGraphInput\n\n\n"
        "class ScriptedTransitionDouble:\n"
        "    def __init__(self, case: StateGraphCase):\n"
        "        self.case = case\n"
        "        self._state = case.before\n"
        "        self._called = False\n\n"
        "    def snapshot(self):\n"
        "        return self._state\n\n"
        "    def input(self) -> StateGraphInput:\n"
        "        return self.case.input\n\n"
        "    def call(self, value: StateGraphInput) -> Any:\n"
        "        if value != self.case.input:\n"
        "            raise AssertionError(f\"unexpected input for {self.case.name}: {value!r}\")\n"
        "        if self._called:\n"
        "            raise AssertionError(f\"case already consumed: {self.case.name}\")\n"
        "        self._called = True\n"
        "        self._state = self.case.after\n"
        "        return self.case.output\n"
    )


def render_validators() -> str:
    return (
        "from __future__ import annotations\n\n"
        "from .types import StateGraphCase, StateGraphRejection\n\n\n"
        "def assert_rejection_is_inert(case: StateGraphCase) -> None:\n"
        "    \"\"\"A negative case must assert refusal AND that nothing moved.\n\n"
        "    Checking only the status would let a program that refuses the call and\n"
        "    still mutates state pass, which is half a guard.\n"
        "    \"\"\"\n"
        "    if not isinstance(case.output, StateGraphRejection):\n"
        "        return\n"
        "    assert case.after == case.before, (\n"
        "        f\"negative case {case.name} is not inert: a refused call changed state\"\n"
        "    )\n\n\n"
        "def assert_case_replays(case: StateGraphCase) -> None:\n"
        "    changed = {\n"
        "        field: {\"before\": case.before.get(field), \"after\": case.after.get(field)}\n"
        "        for field in sorted(set(case.before) | set(case.after))\n"
        "        if case.before.get(field) != case.after.get(field)\n"
        "    }\n"
        "    if hasattr(case.output, \"changed\"):\n"
        "        assert case.output.changed == changed\n"
    )


def render_docs(
    module: str,
    view: str,
    state_count: int,
    transition_count: int,
    emitted_transition_count: int,
    total_transition_count: int,
    dedupe: str,
    *,
    negative: str = "off",
    negative_report: "NegativeCorpusReport | None" = None,
    projector_description: str = "none",
    ports: str = "off",
    port_report: "PortCorpusReport | None" = None,
) -> str:
    body = (
        f"# {module} TLC Cases\n\n"
        "Generated from a TLC DOT state graph dump.\n\n"
        f"- View: `{view}`\n"
        f"- States: `{state_count}`\n"
        f"- Cases: `{transition_count}`\n\n"
        f"- Emitted transitions before dedupe: `{emitted_transition_count}`\n"
        f"- TLC transitions before view filtering: `{total_transition_count}`\n\n"
        f"- Dedupe mode: `{dedupe}`\n"
        # RC-02-DF-04 / MF026-R4-F-01: a corpus that fits its cap must say what
        # made it fit. A count with no projection named is unciteable -- the
        # next reader cannot tell a tractable model from a discarded one.
        f"- State projection: `{projector_description}`\n"
        f"- Negative corpus: `{negative}`\n"
        f"- Port corpus: `{ports}`\n\n"
        "Each positive case is one action-labeled edge in the reachable state graph.\n"
    )
    if negative_report is not None:
        body += (
            "\n## Negative cases\n\n"
            f"- Emitted: `{negative_report.emitted}` of `{negative_report.candidates}` "
            "candidate (state, action, argument) triples\n"
            f"- Negated actions: `{', '.join(negative_report.negated) or 'none'}`\n"
            f"- Negative dedupe: `{negative_report.dedupe_mode}` "
            f"(collapsed `{negative_report.emitted + negative_report.deduped_from}` -> "
            f"`{negative_report.emitted}`)\n"
            f"- Enabled edges cross-checked against the same evaluator: "
            f"`{negative_report.crosschecked_edges}`, of which "
            f"`{sum(negative_report.crosscheck_failures.values())}` disagreed\n\n"
            "A negative case asserts that the program REFUSES the call and that no\n"
            "modeled variable changes. Its `output` is a `StateGraphRejection` whose\n"
            "`reason` is the violated conjunct, verbatim from the module.\n"
        )
    if port_report is not None:
        body += (
            "\n## Port cases\n\n"
            f"- Manifest: `{port_report.manifest}`\n"
            f"- Emitted: `{port_report.emitted}` from `{port_report.source_cases}` source case(s)\n"
            f"- Port dedupe: `{port_report.dedupe_mode}` "
            f"(collapsed `{port_report.emitted + port_report.deduped_from}` -> "
            f"`{port_report.emitted}`)\n\n"
            "| port | cases | emitted | silent | region | declared by |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
        )
        for qualified, block in sorted(port_report.per_port.items()):
            body += (
                f"| `{qualified}` | {block['cases']} | {block['emitted']} | {block['silent']} "
                f"| `{', '.join(block['region'])}` "
                f"| {', '.join(block['declared_actions']) or '(nobody)'} |\n"
            )
        body += (
            "\nA port case asserts the transition over the port's OWN REGION -- the modeled\n"
            "variables written only by actions that declare it -- and carries\n"
            "`port-expect:emitted` when the manifest declares the action on the port and\n"
            "`port-expect:silent` when it maps the action and does not. An action ABSENT\n"
            "from `effects.actions` gets no port case at all: absent means unmapped, and an\n"
            "empty list means checked with no distinct effect.\n"
        )
        if port_report.skipped_ports:
            body += "\nPorts with no case set:\n\n"
            for qualified, why in sorted(port_report.skipped_ports.items()):
                body += f"- `{qualified}` — {why}\n"
        if port_report.undeclared_region_writes or port_report.declared_but_inert:
            body += "\nDeclaration checked against the model's write behaviour:\n\n"
            for pair, count in sorted(port_report.undeclared_region_writes.items()):
                body += (
                    f"- `{pair}` — {count} of {port_report.pair_cases.get(pair, 0)} case(s) "
                    "move the region without declaring the port\n"
                )
            for pair, count in sorted(port_report.declared_but_inert.items()):
                body += (
                    f"- `{pair}` — {count} of {port_report.pair_cases.get(pair, 0)} accepted "
                    "case(s) declare the port and leave the region inert\n"
                )
    return body


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def resolve_module_search_path(
    tla_path: Path, extra_roots: list[Path]
) -> "case_modules.ModuleSearchPath | None":
    """Resolve the EXTENDS hierarchy and report where each module came from.

    EV-02-DF-02. Returns None when the hierarchy cannot be resolved statically
    AND the operator has already supplied a ``TLA-Library`` of their own -- in
    that case this resolver is not the authority and generation proceeds with
    whatever the environment says. In every other case an unresolvable EXTENDS
    is fatal HERE, with the module named, because TLC will fail on it anyway and
    its message is thirty lines lower.
    """
    try:
        search_path = case_modules.resolve_search_path(tla_path, extra_roots)
    except case_modules.ModuleSearchError as error:
        if f"-D{case_modules.TLA_LIBRARY_PROPERTY}" in os.environ.get("JAVA_TOOL_OPTIONS", ""):
            print(
                f"warning: {error}\n"
                f"  JAVA_TOOL_OPTIONS already sets {case_modules.TLA_LIBRARY_PROPERTY}, so "
                "the environment is the authority here and generation proceeds.",
                file=sys.stderr,
            )
            return None
        raise SystemExit(f"ERROR: {error}") from error
    if not search_path.is_self_contained:
        print(
            f"module search path: {', '.join(str(d) for d in search_path.directories)}\n"
            f"  EXTENDS resolved outside {search_path.root.parent}: {search_path.describe()}"
        )
    return search_path


def build_recipes_for_hierarchy(
    tla_path: Path, search_path: "case_modules.ModuleSearchPath | None"
) -> dict[str, "ActionRecipe"]:
    """MF-029 recipes over the whole EXTENDS hierarchy, base modules first.

    A case module declares no VARIABLES and no actions -- every action it enters
    is defined in the view it EXTENDS -- so reading only its own text produced
    recipes for nothing, every case carried no argument, and the adapters then
    refused the entire corpus with ``no usable argument for `i```. Measured on
    the ex4 fixture: the view's own corpus recovered 330/330 arguments while its
    two case modules recovered 0/50 and 0/6 from the same actions.

    The recipes must come from the same module set TLC explored, which is
    exactly what the search path resolved. On a single-file spec that extends
    only standard modules this is the module's own text and nothing changes.
    """
    files = search_path.files_base_first if search_path is not None else (Path(tla_path),)
    return build_recipes(
        "\n".join(Path(path).read_text(encoding="utf-8") for path in files)
    )


def report_out_resolution(requested: Path, resolved: Path, spec_dir: Path) -> None:
    """Say out loud where a relative ``--out`` landed, when it is not obvious.

    EV-02: `--out generated` from a repo root silently created
    ``<spec dir>/generated``. The resolution rule is deliberate (a spec-relative
    default keeps generated corpora beside their spec), but it is a surprise the
    first time, and the run that hit it only found the directory afterwards.
    """
    if Path(requested).is_absolute():
        return
    cwd_candidate = (Path.cwd() / requested).resolve()
    if cwd_candidate == resolved or is_relative_to(resolved, cwd_candidate):
        return
    print(
        f"note: --out {requested} resolved to {resolved} -- a relative --out is "
        f"resolved against the SPEC DIRECTORY ({spec_dir}), not the current "
        f"directory ({Path.cwd()}). Pass an absolute path to control it."
    )


def advise_complexity(
    tla_path: Path,
    cfg_path: Path,
    spec_dir: Path,
    search_path: "case_modules.ModuleSearchPath | None" = None,
) -> None:
    """Print the complexity scan as ADVICE before generating cases (MF-036).

    Complexity is a scanner, not a gate
    (references/architecture_tractability.md, "Advisory, Not Blocking").
    Generation ALWAYS proceeds: a dense model is a finding the agent should
    read, not a blocked build. The scan runs first only so its findings
    appear before the (potentially long) TLC exploration, never
    to refuse it. A model the scan cannot analyze is surfaced the same way --
    reported, not refused -- because TLC may handle a model the static scanner
    cannot.
    """
    manifest_path = case_modules.resolve_manifest_path(spec_dir, search_path)
    try:
        from scripts.analyze_complexity import gate_report
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import gate_report  # type: ignore[no-redef]

    try:
        clean, message = gate_report(
            tla_path,
            cfg_path,
            manifest_path if manifest_path.is_file() else None,
            search_path=list(search_path.directories) if search_path is not None else None,
        )
    except Exception as exc:  # a scan that cannot parse must not block generation
        print(f"warning: complexity scan could not analyze {tla_path}: {exc}", file=sys.stderr)
        return

    if clean:
        print(message)
        return
    print(message, file=sys.stderr)
    print(
        "\nProceeding with case generation -- complexity is advisory and does not block. "
        "Read the findings above (references/architecture_tractability.md, "
        "'Advisory, Not Blocking').",
        file=sys.stderr,
    )


def report_param_recovery(
    prepared: list[PreparedCase],
    param_recipes: dict[str, ActionRecipe],
    package_dir: Path,
) -> CorpusMeasurement:
    """Write the recoverability audit FROM THE CORPUS IT AUDITS, and report it.

    RP-02. The audit used to be rendered from ``param_recipes`` alone -- a
    reading of the module's syntax -- so it printed "Every parameter of every
    action is recoverable from its state pair" over a run that had just
    reported ``0/38 cases carry arguments`` (EV-02-DF-03). A mechanism NAMED is
    not an argument RECOVERED, and only the corpus knows which happened.

    Nothing here filters, samples or truncates: every prepared case is counted,
    including the ones whose arguments failed to recover, because an
    unrecovered argument is a finding to report and not a case to drop.
    """
    audit_path = package_dir / "param_recovery_audit.md"
    measurement = measure_recovery((case.edge.action, case.params) for case in prepared)
    write(audit_path, render_audit(param_recipes, measurement))
    with_params = sum(1 for case in prepared if case.params)
    recovered = sum(
        1 for case in prepared if case.params and not unchecked_param_names(case.params)
    )
    unchecked = sum(1 for case in prepared if unchecked_param_names(case.params))
    print(
        f"parameter recovery: {with_params}/{len(prepared)} cases carry arguments, "
        f"{recovered} carry a fully recovered argument set, "
        f"{unchecked} carry at least one UNCHECKED argument (kept, never dropped); "
        f"audit written to {audit_path}"
    )
    for item in measurement.unrecovered:
        print(
            f"  UNRECOVERABLE on this corpus: {item.action}({item.param}) -- "
            f"0 of {item.cases} cases carry an argument"
        )
    for item in measurement.partial:
        print(
            f"  PARTIAL on this corpus: {item.action}({item.param}) -- "
            f"{item.recovered} of {item.cases} cases carry an argument"
        )
    return measurement



def _relative_source(package_dir: Path) -> str:
    """`package_dir` relative to the repository root, or its name as a floor.

    Never absolute: the value is committed beside generated corpora, and an
    absolute path makes the record differ per checkout for no reader's benefit.
    """
    resolved = Path(package_dir).resolve()
    for parent in [resolved, *resolved.parents]:
        if (parent / ".git").exists():
            try:
                return str(resolved.relative_to(parent))
            except ValueError:
                break
    return resolved.name


def report_action_coverage(
    prepared: list[PreparedCase],
    *,
    module: str,
    view: str,
    action_metadata: dict[str, ActionMetadata],
    package_dir: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Report per-action coverage for the corpus just written, and record it.

    Two things happen here, both advisory:

    * **R4-DF-04** -- a declared view action that generated ZERO cases is a
      silent coverage hole, most often caused by a pure alias wrapper
      (``CliAdd(t) == AddTask(t)``): TLC attributes such edges to the inner
      action's definition site, so the wrapper never appears in the dump.
    * **CM-F2** -- when the module is declared in the manifest's
      ``case_modules:`` block, that warning is scoped to the actions the module
      says it enters. A slice deliberately does not enter the rest of the view,
      and warning about them diagnosed a design decision as a defect: a
      four-action slice of an eleven-action view emitted seven wrong warnings,
      which is how a real warning stops being read.

    Nothing here can refuse a generation; the corpus is already on disk.
    """
    emitted_counts: dict[str, int] = {}
    for case in prepared:
        emitted_counts[case.edge.action] = emitted_counts.get(case.edge.action, 0) + 1
    declared_for_view = {
        name for name, meta in action_metadata.items() if should_emit_action(meta, view)
    }

    declaration = case_modules.declaration_for(manifest_path, module, warn_stream=sys.stderr)
    if declaration is None:
        reportable = declared_for_view
    else:
        scope = set(declaration.actions)
        reportable = declared_for_view & scope
        out_of_view = sorted(scope - declared_for_view)
        out_of_scope = sorted(set(emitted_counts) - scope)
        print(
            f"case module {module}: declared {declaration.form} of {declaration.extends} "
            f"with {len(scope)} action(s) in scope; "
            f"{len(declared_for_view - scope)} other declared {view} action(s) are outside "
            "this aspect and are NOT reported as coverage holes "
            f"(spec_manifest.yaml {case_modules.CASE_MODULES_KEY}:)"
        )
        if declaration.form == "given" and declaration.claim:
            print(f"case module {module}: recorded Given claim -- {declaration.claim}")
        for name in out_of_view:
            print(
                f"warning: case module {module} declares {name!r} in its action scope, "
                f"but actions.yml does not declare it as a {view} action.",
                file=sys.stderr,
            )
        for name in out_of_scope:
            print(
                f"warning: case module {module} generated {emitted_counts[name]} case(s) for "
                f"{name!r}, which is not in its declared `actions:` scope. The declaration "
                "is out of date, and the coverage report is reading it.",
                file=sys.stderr,
            )

    # ZERO IS DECLARABLE; UNDECLARED ZERO IS A FAILURE.
    #
    # This used to be a warning and nothing more: the generator printed a line,
    # `case_coverage.json` simply had no entry for the action, and the corpus
    # reported a healthy total. A corpus that silently covers 10 of 11 declared
    # actions while reporting a five-figure case count is claiming more than it
    # checked -- and it was, in a case where the missing action was the one the
    # goal was written about.
    #
    # Two causes produce the same zero and they are NOT the same thing:
    #   A. an alias wrapper with no conjunct of its own, so TLC attributes its
    #      transitions to the inner action -- A REAL DEFECT;
    #   B. a guard that is unsatisfiable in this epic because the actions that
    #      would satisfy it are sequenced later -- A LEGITIMATE STATE.
    # From the outside they were indistinguishable. `expected_zero: "<why>"`
    # is what makes B sayable, so that A can be made to fail.
    silent = sorted(reportable - set(emitted_counts))
    declared_zero: dict[str, str] = {}
    undeclared_zero: list[str] = []
    for name in silent:
        reason = action_metadata_for(name, view, action_metadata).expected_zero
        if reason:
            declared_zero[name] = reason
        else:
            undeclared_zero.append(name)

    for name, reason in declared_zero.items():
        print(
            f"declared zero: {view} action {name!r} generated no cases, as declared "
            f"in actions.yml -- {reason}"
        )

    for name in undeclared_zero:
        print(
            f"ERROR: declared {view} action {name!r} generated ZERO cases and does "
            "not declare that it should.\n"
            "  If it is a pure alias wrapper (Wrapper(x) == Inner(x)), TLC "
            "attributes its transitions to the inner action -- add a semantic "
            "no-op anchoring conjunct so the wrapper owns its edges.\n"
            "  If it is not a real view action, remove it from actions.yml.\n"
            f"  If the zero is EXPECTED, declare it: `{name}: {{expected_zero: "
            '"<why>"}}` in actions.yml, and the reason is printed on every run.',
            file=sys.stderr,
        )

    record = case_modules.coverage_record(
        module=module,
        view=view,
        action_counts=emitted_counts,
        declared_view_actions=declared_for_view,
        declaration=declaration,
        # RELATIVE, not str(package_dir). An absolute path here is the checkout
        # that last regenerated the corpus, so a tracked record encodes one
        # operator's worktree: measured 2026-09-21, all six tracked
        # case_coverage.json files carried an absolute path and they came from
        # TWO different worktrees (wt-334-plugin-migration x4,
        # tla-spec-dev-2 x2). Regenerating in a third rewrote four of them and
        # dirtied the tree, which then made `skt ticket new` refuse its
        # clean-slate guard and read as a front-door regression.
        #
        # Nothing consumes this field -- build_report never reads it (its own
        # `source` at case_modules.py:608 (view_action_source) is a different
        # thing), and read_coverage_record validates only `module` and stamps
        # `path`. It is redundant with the record's own location, because
        # write_coverage_record writes INTO package_dir.
        source=_relative_source(package_dir),
    )
    record["declared_zero_actions"] = dict(sorted(declared_zero.items()))
    record["undeclared_zero_actions"] = undeclared_zero
    path = case_modules.write_coverage_record(package_dir, record)
    print(f"per-action coverage recorded to {path}")
    if undeclared_zero:
        # The corpus is not what it claims to be, and the caller must not read
        # it as though it were. Raised rather than returned so no caller can
        # forget to check, and after the record is written so the evidence of
        # WHY it failed is on disk.
        raise ZeroCaseActionError(view, undeclared_zero, path)
    return record


# ==========================================================================
# THE NEGATIVE CORPUS -- disabled edges, asserted rejected (HP-03)
# ==========================================================================
#
# THE MEASURED ZERO THIS EXISTS FOR. A corpus built from a TLC state graph
# replays only ENABLED edges, so it contains no rejected inputs, so a service
# that accepts what the model forbids passes every case. Guard relaxation
# measured 0 of 3 (round 1), 0 of 3 on both arms (round 2) and 0 of 4 on an
# independent blind catalogue. RP-02 then counted the mechanism: all 330
# recovered arguments were arguments the guard ACCEPTS, 0 were rejected
# inputs, and 220 refusable pairs existed in the state space that a state
# graph can never emit. Parameter recovery is NOT the cause and fixing it
# moved nothing -- that hypothesis is dead and retracted.
#
# WHAT THIS DOES INSTEAD. At every reachable state, for every action, over
# every argument tuple its quantifier domains admit, evaluate the action's own
# body against that state. Where it is definitely FALSE the action is
# DISABLED there, and the corpus emits one case saying so: the program must
# REJECT this call, and no modeled variable may change.
#
# SOUNDNESS, AND WHY IT IS ONE-SIDED ON PURPOSE. Evaluation is three-valued
# (Kleene): TRUE, FALSE, or UNKNOWN. Anything this evaluator does not
# implement -- a primed variable, EXCEPT, CASE, LET, an unresolvable operator,
# a domain it cannot enumerate -- is UNKNOWN, never a default. A conjunction
# is FALSE only when some conjunct is FALSE; a disjunction only when every
# disjunct is. So an unsupported construct costs COMPLETENESS (a refusable
# input nobody tests) and can never cost SOUNDNESS (an accepted input asserted
# rejected). That asymmetry is the whole design: the acceptance criterion
# "zero false rejections on the green control" is a property of the algorithm,
# not of how carefully the fixture was chosen.
#
# NO MODEL SURFACE IS ADDED. surface_cost_rule: this is a per-flag variant of
# the existing `generate cases` command, which semantic_model_rule places
# out-of-model, and it performs no effect the GenerateCases action does not
# already declare -- it reads the same .tla/.cfg and writes into the same
# generated package under the same `spec_tree` port. No new action, no new
# variable, no new port, 1x the state space, and no second TLC run.


class Unevaluable(Exception):
    """A fragment this generator declines to evaluate.

    Raised and caught, never absorbed into a truth value. Every catch site
    turns it into UNKNOWN, which can only ever suppress a negative case.
    """


#: Maximum operator-expansion depth. A model that needs more than this is
#: reported as unevaluable rather than explored further.
_MAX_EXPANSION_DEPTH = 16

#: Largest set ``SUBSET`` will expand. Beyond it the expression is UNKNOWN.
_MAX_POWERSET_BASE = 12

_TLA_TOKEN_RE = re.compile(
    r"""
      (?P<STRING>"(?:[^"\\]|\\.)*")
    | (?P<NUMBER>\d+)
    | (?P<WORDOP>\\(?:notin|subseteq|subset|union|intersect|cup|cap|times|div|leq|geq|neq|land|lor|lnot|in|A|E|X|o)(?![A-Za-z0-9_]))
    | (?P<OR>\\/)
    | (?P<AND>/\\)
    | (?P<SETMINUS>\\)
    | (?P<SYM><=>|=>|<<|>>|\|->|:>|@@|\.\.|->|<=|>=|/=|\#|~|=|<|>|\+|-|\*|\(|\)|\[|\]|\{|\}|,|:|')
    | (?P<NAME>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<WS>\s+)
    """,
    re.VERBOSE,
)

_WORDOP_CANON = {
    r"\leq": "<=",
    r"\geq": ">=",
    r"\neq": "#",
    r"\land": "/\\",
    r"\lor": "\\/",
    r"\lnot": "~",
    r"\union": "\\cup",
    r"\intersect": "\\cap",
}

_TLA_KEYWORDS = frozenset(
    {"IF", "THEN", "ELSE", "TRUE", "FALSE", "DOMAIN", "SUBSET", "UNION", "EXCEPT", "LET", "IN", "CASE", "OTHER", "CHOOSE"}
)


def tokenize_tla(text: str) -> list[str]:
    """Tokens of a TLA+ expression, or ``Unevaluable`` on an unknown character."""
    tokens: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        match = _TLA_TOKEN_RE.match(text, index)
        if match is None:
            raise Unevaluable(f"unrecognized character at offset {index}: {text[index:index + 12]!r}")
        index = match.end()
        kind = match.lastgroup
        if kind == "WS":
            continue
        value = match.group()
        if kind == "WORDOP":
            value = _WORDOP_CANON.get(value, value)
        tokens.append(value)
    return tokens


class _TlaParser:
    """A recursive-descent parser for the constrained profile's expressions.

    Deliberately partial. Every construct it does not implement raises
    ``Unevaluable``, which the three-valued evaluator turns into UNKNOWN.
    """

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    # -- token helpers ---------------------------------------------------
    def peek(self, offset: int = 0) -> str | None:
        index = self.pos + offset
        return self.tokens[index] if index < len(self.tokens) else None

    def next(self) -> str:
        token = self.peek()
        if token is None:
            raise Unevaluable("unexpected end of expression")
        self.pos += 1
        return token

    def accept(self, token: str) -> bool:
        if self.peek() == token:
            self.pos += 1
            return True
        return False

    def expect(self, token: str) -> None:
        if not self.accept(token):
            raise Unevaluable(f"expected {token!r}, found {self.peek()!r}")

    # -- grammar ---------------------------------------------------------
    def parse(self) -> Any:
        node = self.expression()
        if self.pos != len(self.tokens):
            raise Unevaluable(f"trailing tokens from {self.peek()!r}")
        return node

    def expression(self) -> Any:
        return self.equivalence()

    def equivalence(self) -> Any:
        node = self.implication()
        while self.peek() == "<=>":
            self.next()
            node = ("binop", "<=>", node, self.implication())
        return node

    def implication(self) -> Any:
        node = self.disjunction()
        while self.peek() == "=>":
            self.next()
            node = ("binop", "=>", node, self.disjunction())
        return node

    def disjunction(self) -> Any:
        node = self.conjunction()
        while self.peek() == "\\/":
            self.next()
            node = ("binop", "\\/", node, self.conjunction())
        return node

    def conjunction(self) -> Any:
        node = self.negation()
        while self.peek() == "/\\":
            self.next()
            node = ("binop", "/\\", node, self.negation())
        return node

    def negation(self) -> Any:
        if self.accept("~"):
            return ("unop", "~", self.negation())
        return self.comparison()

    _COMPARISONS = ("=", "#", "/=", "<", ">", "<=", ">=", "\\in", "\\notin", "\\subseteq", "\\subset")

    def comparison(self) -> Any:
        node = self.additive()
        token = self.peek()
        if token in self._COMPARISONS:
            self.next()
            return ("binop", token, node, self.additive())
        return node

    def additive(self) -> Any:
        node = self.multiplicative()
        while self.peek() in ("+", "-", "\\cup", "\\"):
            operator = self.next()
            node = ("binop", operator, node, self.multiplicative())
        return node

    def multiplicative(self) -> Any:
        node = self.rangeexpr()
        while self.peek() in ("*", "\\div", "\\cap"):
            operator = self.next()
            node = ("binop", operator, node, self.rangeexpr())
        return node

    def rangeexpr(self) -> Any:
        node = self.postfix()
        if self.peek() == "..":
            self.next()
            return ("range", node, self.postfix())
        return node

    def postfix(self) -> Any:
        node = self.primary()
        while True:
            token = self.peek()
            if token == "[":
                self.next()
                index = self.expression()
                self.expect("]")
                node = ("apply", node, index)
                continue
            if token == "'":
                self.next()
                node = ("primed", node)
                continue
            break
        return node

    def primary(self) -> Any:
        token = self.peek()
        if token is None:
            raise Unevaluable("unexpected end of expression")
        if token.startswith('"'):
            self.next()
            return ("const", ast.literal_eval(token))
        if token.isdigit():
            self.next()
            return ("const", int(token))
        if token == "-":
            self.next()
            return ("unop", "-", self.postfix())
        if token == "(":
            self.next()
            node = self.expression()
            self.expect(")")
            return node
        if token == "<<":
            self.next()
            items = []
            if self.peek() != ">>":
                items.append(self.expression())
                while self.accept(","):
                    items.append(self.expression())
            self.expect(">>")
            return ("tuple", tuple(items))
        if token == "{":
            return self.set_expression()
        if token == "[":
            return self.bracket_expression()
        if token in ("\\A", "\\E"):
            self.next()
            bindings = self.bindings()
            self.expect(":")
            return ("quant", token, bindings, self.expression())
        if token == "IF":
            self.next()
            condition = self.expression()
            self.expect("THEN")
            consequent = self.expression()
            self.expect("ELSE")
            return ("if", condition, consequent, self.expression())
        if token in ("DOMAIN", "SUBSET", "UNION"):
            self.next()
            return ("unop", token, self.postfix())
        if token == "TRUE":
            self.next()
            return ("const", True)
        if token == "FALSE":
            self.next()
            return ("const", False)
        if token in _TLA_KEYWORDS:
            raise Unevaluable(f"unsupported construct: {token}")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            self.next()
            if self.peek() == "(":
                self.next()
                args = []
                if self.peek() != ")":
                    args.append(self.expression())
                    while self.accept(","):
                        args.append(self.expression())
                self.expect(")")
                return ("call", token, tuple(args))
            return ("name", token)
        raise Unevaluable(f"unsupported token {token!r}")

    def bindings(self) -> tuple[tuple[tuple[str, ...], Any], ...]:
        bindings: list[tuple[tuple[str, ...], Any]] = []
        while True:
            names = [self.next()]
            while self.accept(","):
                names.append(self.next())
            self.expect("\\in")
            domain = self.multiplicative()
            for name in names:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                    raise Unevaluable(f"bad binding name {name!r}")
            bindings.append((tuple(names), domain))
            if self.peek() == "," and self.peek(2) == "\\in":
                self.next()
                continue
            if self.peek() == "," and self.peek(1) is not None and self.peek(3) == "\\in":
                self.next()
                continue
            break
        return tuple(bindings)

    def set_expression(self) -> Any:
        self.expect("{")
        if self.accept("}"):
            return ("set", ())
        mark = self.pos
        # {x \in S : P}
        if self.peek(1) == "\\in":
            try:
                bindings = self.bindings()
                self.expect(":")
                predicate = self.expression()
                self.expect("}")
                return ("setfilter", bindings, predicate)
            except Unevaluable:
                self.pos = mark
        items = [self.expression()]
        while self.accept(","):
            items.append(self.expression())
        if self.accept(":"):
            bindings = self.bindings()
            self.expect("}")
            return ("setmap", items[0], bindings)
        self.expect("}")
        return ("set", tuple(items))

    def bracket_expression(self) -> Any:
        self.expect("[")
        mark = self.pos
        # [x \in S |-> e]
        if self.peek(1) == "\\in":
            try:
                bindings = self.bindings()
                self.expect("|->")
                body = self.expression()
                self.expect("]")
                return ("funcctor", bindings, body)
            except Unevaluable:
                self.pos = mark
        # [a |-> e, b |-> e]
        try:
            fields: list[tuple[str, Any]] = []
            while True:
                key = self.next()
                self.expect("|->")
                fields.append((key, self.expression()))
                if not self.accept(","):
                    break
            self.expect("]")
            return ("record", tuple(fields))
        except Unevaluable:
            self.pos = mark
        raise Unevaluable("unsupported bracket expression (EXCEPT, function set, ...)")


_PARSE_CACHE: dict[str, Any] = {}


def parse_tla_expression(text: str) -> Any:
    """Parse one TLA+ expression, memoized on its exact source text."""
    cached = _PARSE_CACHE.get(text)
    if cached is not None:
        if isinstance(cached, Unevaluable):
            raise cached
        return cached
    try:
        node = _TlaParser(tokenize_tla(text)).parse()
    except Unevaluable as error:
        _PARSE_CACHE[text] = error
        raise
    except RecursionError as error:  # pragma: no cover - pathological input
        wrapped = Unevaluable("expression nesting too deep")
        _PARSE_CACHE[text] = wrapped
        raise wrapped from error
    _PARSE_CACHE[text] = node
    return node


@dataclass(frozen=True)
class TlaDefinition:
    name: str
    params: tuple[str, ...]
    body: str


def parse_tla_definitions(source: str) -> dict[str, TlaDefinition]:
    """Top-level ``Name(params) == body`` definitions of a module."""
    try:
        from scripts.analyze_complexity import parse_definitions, strip_comments
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import parse_definitions, strip_comments  # type: ignore[no-redef]

    definitions: dict[str, TlaDefinition] = {}
    for definition in parse_definitions(strip_comments(source)):
        definitions[definition.name] = TlaDefinition(
            name=definition.name,
            params=tuple(definition.params),
            body=definition.body,
        )
    return definitions


def coerce_cfg_constant(value: Any) -> Any:
    """A ``.cfg`` constant assignment as an evaluable value.

    A set assignment becomes a ``frozenset`` of atoms; a scalar becomes its
    atom. TLC model values (``NoRoot = NoRoot``) stay strings, which is what
    the DOT parser produces for them too, so the two sides compare.
    """
    if isinstance(value, list):
        return frozenset(parse_atom(str(item)) for item in value)
    return parse_atom(str(value))


def _tla_function_key(value: Any) -> str:
    return str(value)


class GuardEvaluator:
    """Three-valued evaluation of an action body against one concrete state.

    ``evaluate`` answers TRUE / FALSE / UNKNOWN (``None``). Only FALSE is ever
    acted on. See the section header for why that asymmetry is the soundness
    argument rather than a convenience.
    """

    def __init__(
        self,
        definitions: dict[str, TlaDefinition],
        constants: dict[str, Any],
        variables: tuple[str, ...],
    ):
        self.definitions = definitions
        self.constants = constants
        self.variables = variables
        self._bullets: dict[str, tuple[str | None, tuple[str, ...]]] = {}

    # -- bullet structure -------------------------------------------------
    def split_bullets(self, text: str) -> tuple[str | None, tuple[str, ...]]:
        """TLA+'s indentation-delimited ``/\\``/``\\/`` list, if this text is one.

        Returns ``(kind, items)`` with ``kind`` in ``{"/\\", "\\/", None}``.
        ``None`` means the text is a leaf to be parsed as one expression.

        This is the real bulleted-list rule -- the bullets of one list share a
        column -- and not a textual split on ``/\\``. A textual split tears
        ``/\\ \\/ /\\ a /\\ b \\/ c`` into fragments and would promote ``a`` to
        a top-level conjunct it is not, which is the one way this design could
        emit a false rejection.
        """
        cached = self._bullets.get(text)
        if cached is not None:
            return cached
        result = self._compute_bullets(text)
        self._bullets[text] = result
        return result

    def _compute_bullets(self, text: str) -> tuple[str | None, tuple[str, ...]]:
        positions: list[tuple[int, int, str]] = []  # (column, offset, kind)
        depth = 0
        in_string = False
        column = 0
        line_has_content = False
        index = 0
        while index < len(text):
            char = text[index]
            if char == "\n":
                column = 0
                line_has_content = False
                in_string = False
                index += 1
                continue
            if in_string:
                if char == '"' and not is_escaped(text, index):
                    in_string = False
                column += 1
                index += 1
                continue
            if char == '"':
                in_string = True
                column += 1
                index += 1
                continue
            pair = text[index : index + 2]
            if pair in ("/\\", "\\/") and depth == 0 and not line_has_content:
                positions.append((column, index, pair))
                line_has_content = True
                column += 2
                index += 2
                continue
            if pair == "<<":
                depth += 1
                column += 2
                index += 2
                continue
            if pair == ">>":
                depth -= 1
                column += 2
                index += 2
                continue
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            if not char.isspace():
                line_has_content = True
            column += 1
            index += 1
        if not positions:
            return (None, ())
        least = min(position[0] for position in positions)
        bullets = [position for position in positions if position[0] == least]
        kinds = {position[2] for position in bullets}
        if len(kinds) != 1:
            # Mixed bullets at one column is not a well-formed list. Refuse to
            # guess its structure: the whole body becomes one leaf, and a leaf
            # that will not parse is UNKNOWN.
            return (None, ())
        kind = bullets[0][2]
        if text[: bullets[0][1]].strip():
            # Content before the first bullet means this is not a pure list.
            return (None, ())
        items: list[str] = []
        for order, (_, offset, _) in enumerate(bullets):
            end = bullets[order + 1][1] if order + 1 < len(bullets) else len(text)
            # Blank the bullet token so every remaining line keeps its column.
            item = "  " + text[offset + 2 : end]
            items.append(item)
        return (kind, tuple(items))

    # -- three-valued evaluation ------------------------------------------
    def evaluate(self, text: str, env: dict[str, Any]) -> tuple[bool | None, str | None]:
        """``(truth, witness)``. ``witness`` is the FALSE fragment, verbatim."""
        kind, items = self.split_bullets(text)
        if kind == "/\\":
            unknown = False
            for item in items:
                truth, witness = self.evaluate(item, env)
                if truth is False:
                    return False, witness
                if truth is None:
                    unknown = True
            return (None, None) if unknown else (True, None)
        if kind == "\\/":
            unknown = False
            for item in items:
                truth, _ = self.evaluate(item, env)
                if truth is True:
                    return True, None
                if truth is None:
                    unknown = True
            return (None, None) if unknown else (False, collapse_whitespace(text))
        try:
            value = self.eval_node(parse_tla_expression(text.strip()), env, 0)
        except Unevaluable:
            return None, None
        except RecursionError:  # pragma: no cover - pathological input
            return None, None
        if value is True:
            return True, None
        if value is False:
            return False, collapse_whitespace(text)
        return None, None

    # -- two-valued expression evaluation ---------------------------------
    def eval_node(self, node: Any, env: dict[str, Any], depth: int) -> Any:
        if depth > _MAX_EXPANSION_DEPTH:
            raise Unevaluable("operator expansion too deep")
        kind = node[0]
        if kind == "const":
            return node[1]
        if kind == "name":
            return self.eval_name(node[1], env, depth)
        if kind == "primed":
            raise Unevaluable("primed variable")
        if kind == "call":
            return self.eval_call(node[1], node[2], env, depth)
        if kind == "apply":
            function = self.eval_node(node[1], env, depth)
            index = self.eval_node(node[2], env, depth)
            if isinstance(function, dict):
                key = _tla_function_key(index)
                if key not in function:
                    raise Unevaluable(f"index {key!r} outside function domain")
                return function[key]
            if isinstance(function, tuple):
                if not isinstance(index, int) or not 1 <= index <= len(function):
                    raise Unevaluable("sequence index out of range")
                return function[index - 1]
            raise Unevaluable("application of a non-function")
        if kind == "set":
            return frozenset(freeze_set_member(self.eval_node(item, env, depth)) for item in node[1])
        if kind == "tuple":
            return tuple(self.eval_node(item, env, depth) for item in node[1])
        if kind == "record":
            return {key: self.eval_node(value, env, depth) for key, value in node[1]}
        if kind == "range":
            low = self.eval_node(node[1], env, depth)
            high = self.eval_node(node[2], env, depth)
            if not isinstance(low, int) or not isinstance(high, int):
                raise Unevaluable("non-integer range bound")
            return frozenset(range(low, high + 1))
        if kind == "if":
            condition = self.eval_node(node[1], env, depth)
            if not isinstance(condition, bool):
                raise Unevaluable("non-boolean IF condition")
            return self.eval_node(node[2] if condition else node[3], env, depth)
        if kind == "unop":
            return self.eval_unop(node[1], node[2], env, depth)
        if kind == "binop":
            return self.eval_binop(node[1], node[2], node[3], env, depth)
        if kind == "quant":
            return self.eval_quantifier(node[1], node[2], node[3], env, depth)
        if kind == "funcctor":
            bindings = self.eval_bindings(node[1], env, depth)
            if len(bindings) != 1 or len(bindings[0][0]) != 1:
                raise Unevaluable("multi-argument function constructor")
            name = bindings[0][0][0]
            return {
                _tla_function_key(value): self.eval_node(node[2], {**env, name: value}, depth)
                for value in sorted(bindings[0][1], key=repr)
            }
        if kind == "setfilter":
            bindings = self.eval_bindings(node[1], env, depth)
            if len(bindings) != 1 or len(bindings[0][0]) != 1:
                raise Unevaluable("multi-variable set filter")
            name = bindings[0][0][0]
            selected = []
            for value in sorted(bindings[0][1], key=repr):
                truth = self.eval_node(node[2], {**env, name: value}, depth)
                if not isinstance(truth, bool):
                    raise Unevaluable("non-boolean set filter")
                if truth:
                    selected.append(freeze_set_member(value))
            return frozenset(selected)
        if kind == "setmap":
            bindings = self.eval_bindings(node[2], env, depth)
            produced = []
            for assignment in self.iter_assignments(bindings):
                produced.append(freeze_set_member(self.eval_node(node[1], {**env, **assignment}, depth)))
            return frozenset(produced)
        raise Unevaluable(f"unsupported node {kind}")

    def eval_name(self, name: str, env: dict[str, Any], depth: int) -> Any:
        if name in env:
            return env[name]
        if name in self.constants:
            return self.constants[name]
        definition = self.definitions.get(name)
        if definition is not None and not definition.params:
            return self.eval_node(parse_tla_expression(definition.body.strip()), {}, depth + 1)
        if name in self.variables:
            raise Unevaluable(f"variable {name} absent from this state")
        raise Unevaluable(f"unbound name {name}")

    def eval_call(self, name: str, args: tuple[Any, ...], env: dict[str, Any], depth: int) -> Any:
        values = [self.eval_node(argument, env, depth) for argument in args]
        if name == "Cardinality" and len(values) == 1:
            if not isinstance(values[0], (frozenset, set)):
                raise Unevaluable("Cardinality of a non-set")
            return len(values[0])
        if name == "IsFiniteSet" and len(values) == 1:
            return isinstance(values[0], (frozenset, set))
        if name == "Len" and len(values) == 1:
            if not isinstance(values[0], tuple):
                raise Unevaluable("Len of a non-sequence")
            return len(values[0])
        if name == "Head" and len(values) == 1:
            if not isinstance(values[0], tuple) or not values[0]:
                raise Unevaluable("Head of a non-sequence")
            return values[0][0]
        if name == "Tail" and len(values) == 1:
            if not isinstance(values[0], tuple) or not values[0]:
                raise Unevaluable("Tail of a non-sequence")
            return values[0][1:]
        if name == "Append" and len(values) == 2:
            if not isinstance(values[0], tuple):
                raise Unevaluable("Append to a non-sequence")
            return values[0] + (values[1],)
        definition = self.definitions.get(name)
        if definition is None or len(definition.params) != len(values):
            raise Unevaluable(f"unresolvable operator {name}/{len(values)}")
        inner = dict(zip(definition.params, values))
        node = parse_tla_expression(definition.body.strip())
        return self.eval_node(node, inner, depth + 1)

    def eval_unop(self, operator: str, operand: Any, env: dict[str, Any], depth: int) -> Any:
        value = self.eval_node(operand, env, depth)
        if operator == "~":
            if not isinstance(value, bool):
                raise Unevaluable("negation of a non-boolean")
            return not value
        if operator == "-":
            if not isinstance(value, int) or isinstance(value, bool):
                raise Unevaluable("negation of a non-integer")
            return -value
        if operator == "DOMAIN":
            if isinstance(value, dict):
                return frozenset(value)
            if isinstance(value, tuple):
                return frozenset(range(1, len(value) + 1))
            raise Unevaluable("DOMAIN of a non-function")
        if operator == "SUBSET":
            if not isinstance(value, (frozenset, set)) or len(value) > _MAX_POWERSET_BASE:
                raise Unevaluable("SUBSET of a non-set or an oversized set")
            members = sorted(value, key=repr)
            return frozenset(
                frozenset(combination)
                for size in range(len(members) + 1)
                for combination in itertools.combinations(members, size)
            )
        if operator == "UNION":
            if not isinstance(value, (frozenset, set)):
                raise Unevaluable("UNION of a non-set")
            result: set[Any] = set()
            for member in value:
                if not isinstance(member, (frozenset, set)):
                    raise Unevaluable("UNION over a non-set member")
                result |= set(member)
            return frozenset(result)
        raise Unevaluable(f"unsupported unary {operator}")

    def eval_binop(self, operator: str, left: Any, right: Any, env: dict[str, Any], depth: int) -> Any:
        if operator in ("/\\", "\\/", "=>", "<=>"):
            first = self.eval_node(left, env, depth)
            if not isinstance(first, bool):
                raise Unevaluable("non-boolean operand")
            # Short-circuit so an unevaluable second operand costs nothing when
            # the first already decides the result.
            if operator == "/\\" and first is False:
                return False
            if operator == "\\/" and first is True:
                return True
            if operator == "=>" and first is False:
                return True
            second = self.eval_node(right, env, depth)
            if not isinstance(second, bool):
                raise Unevaluable("non-boolean operand")
            if operator == "/\\":
                return first and second
            if operator == "\\/":
                return first or second
            if operator == "=>":
                return (not first) or second
            return first == second

        first = self.eval_node(left, env, depth)
        second = self.eval_node(right, env, depth)
        if operator == "=":
            return first == second
        if operator in ("#", "/="):
            return first != second
        if operator == "\\in":
            if not isinstance(second, (frozenset, set)):
                raise Unevaluable("membership in a non-set")
            return freeze_set_member(first) in second
        if operator == "\\notin":
            if not isinstance(second, (frozenset, set)):
                raise Unevaluable("membership in a non-set")
            return freeze_set_member(first) not in second
        if operator in ("\\subseteq", "\\subset"):
            if not isinstance(first, (frozenset, set)) or not isinstance(second, (frozenset, set)):
                raise Unevaluable("subset of a non-set")
            return set(first) <= set(second) if operator == "\\subseteq" else set(first) < set(second)
        if operator in ("<", ">", "<=", ">="):
            if not isinstance(first, int) or not isinstance(second, int) or isinstance(first, bool) or isinstance(second, bool):
                raise Unevaluable("comparison of non-integers")
            if operator == "<":
                return first < second
            if operator == ">":
                return first > second
            if operator == "<=":
                return first <= second
            return first >= second
        if operator in ("+", "-", "*", "\\div"):
            if not isinstance(first, int) or not isinstance(second, int) or isinstance(first, bool) or isinstance(second, bool):
                raise Unevaluable("arithmetic on non-integers")
            if operator == "+":
                return first + second
            if operator == "-":
                return first - second
            if operator == "*":
                return first * second
            if second == 0:
                raise Unevaluable("division by zero")
            return first // second
        if operator in ("\\cup", "\\cap", "\\"):
            if not isinstance(first, (frozenset, set)) or not isinstance(second, (frozenset, set)):
                raise Unevaluable("set operation on a non-set")
            if operator == "\\cup":
                return frozenset(set(first) | set(second))
            if operator == "\\cap":
                return frozenset(set(first) & set(second))
            return frozenset(set(first) - set(second))
        raise Unevaluable(f"unsupported operator {operator}")

    def eval_bindings(
        self, bindings: tuple[tuple[tuple[str, ...], Any], ...], env: dict[str, Any], depth: int
    ) -> list[tuple[tuple[str, ...], Any]]:
        resolved = []
        for names, domain_node in bindings:
            domain = self.eval_node(domain_node, env, depth)
            if not isinstance(domain, (frozenset, set)):
                raise Unevaluable("quantifier over a non-set")
            resolved.append((names, domain))
        return resolved

    def iter_assignments(self, bindings: list[tuple[tuple[str, ...], Any]]) -> Any:
        names: list[str] = []
        domains: list[list[Any]] = []
        for group, domain in bindings:
            ordered = sorted(domain, key=repr)
            for name in group:
                names.append(name)
                domains.append(ordered)
        for combination in itertools.product(*domains):
            yield dict(zip(names, combination))

    def eval_quantifier(
        self,
        quantifier: str,
        bindings: tuple[tuple[tuple[str, ...], Any], ...],
        body: Any,
        env: dict[str, Any],
        depth: int,
    ) -> Any:
        resolved = self.eval_bindings(bindings, env, depth)
        results = []
        for assignment in self.iter_assignments(resolved):
            truth = self.eval_node(body, {**env, **assignment}, depth)
            if not isinstance(truth, bool):
                raise Unevaluable("non-boolean quantifier body")
            results.append(truth)
        if quantifier == "\\A":
            return all(results)
        return any(results)


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True)
class ActionSignature:
    """One action of ``Next``, with the domain each argument ranges over."""

    name: str
    params: tuple[str, ...]
    domains: tuple[tuple[Any, ...], ...]
    body: str

    @property
    def candidate_count(self) -> int:
        total = 1
        for domain in self.domains:
            total *= len(domain)
        return total


def resolve_next_relation(cfg_text: str, definitions: dict[str, TlaDefinition]) -> str:
    """The name of this model's next-state relation, read from its own ``.cfg``.

    CA-06-DF-01. ``extract_action_signatures`` defaulted to the literal name
    ``Next`` and NEITHER CALLER EVER OVERRODE IT, so the negative corpus and the
    port corpus emitted ZERO cases on any model that spells its next-state
    relation differently -- while the run still printed ``corpus gate PASS``.
    Measured: ``examples/distributed_history`` names its relations
    ``InternalNext`` and ``ExternalNext`` and got nothing from either mode, and
    every measurement that defends those two modes (``SM-02``'s "guard
    relaxation 3 of 3" and "83.2% executable") is taken on
    ``examples/validation/ab/model/QuotaLedger.tla``, the one model in this
    repository whose relation is literally named ``Next``.

    The resolver is NOT NEW. ``scripts/analyze_complexity.py`` has shipped
    ``find_next_relation`` for three epics -- ``NEXT Name`` in the cfg wins,
    otherwise ``SPECIFICATION Spec`` is followed to the ``[][Next]_vars``
    box-action, transitively through aliases -- and this module simply never
    called it. So this is the DELETION of a hardcoded constant in favour of a
    function the repository already ships and tests, and it is a NO-OP on both
    models that already worked: ``find_next_relation`` returns ``Next`` for
    each, so no sealed corpus moves.

    Falls back to ``Next`` when the cfg names nothing resolvable, which keeps
    the previous behaviour for a model that declares neither NEXT nor a
    followable SPECIFICATION.
    """
    try:
        from scripts.analyze_complexity import find_next_relation
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import find_next_relation  # type: ignore[no-redef]

    return find_next_relation(cfg_text, definitions) or "Next"


def extract_action_signatures(
    definitions: dict[str, TlaDefinition],
    evaluator: GuardEvaluator,
    next_name: str = "Next",
) -> tuple[dict[str, ActionSignature], dict[str, str]]:
    """Signatures from the disjuncts of ``Next``, plus a reason per rejection.

    A disjunct must be ``\\E x \\in S, ... : Name(args)`` or a bare ``Name``,
    with every argument a bound variable of that quantifier and every domain a
    finite set this evaluator can enumerate. Anything else is reported, never
    approximated -- an approximated domain would emit arguments the model does
    not admit.
    """
    try:
        from scripts.analyze_complexity import split_top_level_disjuncts
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import split_top_level_disjuncts  # type: ignore[no-redef]

    signatures: dict[str, ActionSignature] = {}
    rejected: dict[str, str] = {}
    definition = definitions.get(next_name)
    if definition is None:
        return signatures, {next_name: "no such definition"}
    for chunk in split_top_level_disjuncts(definition.body):
        text = collapse_whitespace(chunk)
        if not text:
            continue
        try:
            node = parse_tla_expression(text)
        except Unevaluable as error:
            rejected[text[:60]] = f"disjunct did not parse: {error}"
            continue
        bindings: tuple[tuple[tuple[str, ...], Any], ...] = ()
        if node[0] == "quant" and node[1] == "\\E":
            bindings = node[2]
            node = node[3]
        if node[0] == "name":
            name, arguments = node[1], ()
        elif node[0] == "call":
            name, arguments = node[1], node[2]
        else:
            rejected[text[:60]] = "disjunct is not a call to a named action"
            continue
        action = definitions.get(name)
        if action is None:
            rejected[name] = "action has no definition in this module"
            continue
        try:
            domains_by_name: dict[str, tuple[Any, ...]] = {}
            for names, domain_node in bindings:
                domain = evaluator.eval_node(domain_node, {}, 0)
                if not isinstance(domain, (frozenset, set)):
                    raise Unevaluable("quantifier domain is not a set")
                ordered = tuple(sorted(domain, key=repr))
                for bound in names:
                    domains_by_name[bound] = ordered
        except Unevaluable as error:
            rejected[name] = f"quantifier domain not enumerable: {error}"
            continue
        argument_names: list[str] = []
        for argument in arguments:
            if argument[0] != "name" or argument[1] not in domains_by_name:
                argument_names = []
                break
            argument_names.append(argument[1])
        if len(argument_names) != len(arguments):
            rejected[name] = "an argument is not a plain quantifier-bound variable"
            continue
        if len(action.params) != len(argument_names):
            rejected[name] = "arity of the call does not match the definition"
            continue
        signatures[name] = ActionSignature(
            name=name,
            params=tuple(action.params),
            domains=tuple(domains_by_name[bound] for bound in argument_names),
            body=action.body,
        )
    return signatures, rejected


def guard_read_variables(
    signature: ActionSignature, evaluator: GuardEvaluator
) -> frozenset[str]:
    """Variables read by the unprimed items of an action body."""
    reads: set[str] = set()

    def walk(text: str) -> None:
        kind, items = evaluator.split_bullets(text)
        if kind is not None:
            for item in items:
                walk(item)
            return
        stripped = _STRIP_STRINGS_RE.sub(" ", text)
        if "'" in stripped:
            return
        for token in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped)):
            if token in evaluator.variables:
                reads.add(token)

    walk(signature.body)
    return frozenset(reads)


def written_variables(
    signature: ActionSignature,
    variables: tuple[str, ...],
    definitions: dict[str, TlaDefinition] | None = None,
) -> frozenset[str]:
    """Variables this action assigns, following the operators it calls.

    The expansion matters: HP-01's fixture writes its refusals as
    ``RefuseX(...) == guard /\\ Refuse("reason")``, so the action's own text
    primes nothing at all. Reading only that text reports an empty write set --
    true by accident here, and wrong the moment a model spells one conjunct
    through a helper.
    """
    seen: set[str] = {signature.name}
    written: set[str] = set()
    stack = [signature.body]
    while stack:
        text = _STRIP_STRINGS_RE.sub(" ", stack.pop())
        for variable in variables:
            if re.search(rf"\b{re.escape(variable)}'", text):
                written.add(variable)
        if definitions is None:
            continue
        for token in sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))):
            if token in definitions and token not in seen and token not in variables:
                seen.add(token)
                stack.append(definitions[token].body)
    return frozenset(written)


_STRIP_STRINGS_RE = re.compile(r'"(?:[^"\\]|\\.)*"')


def negatable_actions(
    signatures: dict[str, ActionSignature], evaluator: GuardEvaluator
) -> tuple[list[str], dict[str, str]]:
    """Which actions represent a CALL that a program can be asked to refuse.

    A model may spell its refusals out as their own actions -- HP-01's fixture
    does, and the standing recommendation is to -- and those actions must NOT
    be negated. The complement of "this call is refused" is "this call is
    accepted", so emitting it would assert rejection of an input the model
    ENABLES: precisely the false rejection this mode must never produce.

    The rule that separates them, stated so it can be argued with: an action is
    a call when it WRITES at least one variable that some guard in this module
    READS. A refusal changes no domain state -- it only records an outcome
    nothing is guarded on -- so it fails that test, while every state-advancing
    command passes it. An operator who disagrees overrides the set with
    ``--negative-action``; the chosen and rejected sets are both printed, so
    the decision is visible rather than inferred.
    """
    guard_reads: set[str] = set()
    for signature in signatures.values():
        guard_reads |= guard_read_variables(signature, evaluator)
    chosen: list[str] = []
    excluded: dict[str, str] = {}
    for name in sorted(signatures):
        writes = written_variables(signatures[name], evaluator.variables, evaluator.definitions)
        overlap = writes & guard_reads
        if overlap:
            chosen.append(name)
        else:
            excluded[name] = (
                "writes {" + ", ".join(sorted(writes)) + "}, none of which any guard reads -- "
                "this is a refusal or a pure observation, not a call to be refused"
            )
    return chosen, excluded


@dataclass
class NegativeCorpusReport:
    """Everything the negative pass measured, printed and never summarized away."""

    emitted: int = 0
    candidates: int = 0
    #: Triples the evaluator did NOT prove disabled. A whole action body always
    #: contains primed conjuncts, which are UNKNOWN by construction, so "not
    #: disabled" is the strongest thing this pass can say about them -- it is
    #: never the claim that they are enabled.
    not_disabled: int = 0
    dump_edges_for_negated: int = 0
    negated: tuple[str, ...] = ()
    excluded: dict[str, str] = field(default_factory=dict)
    suppressed: dict[str, str] = field(default_factory=dict)
    per_action: dict[str, int] = field(default_factory=dict)
    per_reason: dict[str, int] = field(default_factory=dict)
    deduped_from: int = 0
    dedupe_mode: str = "none"
    outcome_fields: tuple[str, ...] = ()
    crosschecked_edges: int = 0
    crosscheck_failures: dict[str, int] = field(default_factory=dict)


def negative_cases_for_corpus(
    *,
    states: dict[str, dict[str, Any]],
    edges: list[Edge],
    tla_source: str,
    cfg_text: str,
    view: str,
    action_metadata: dict[str, ActionMetadata],
    state_projector: Any | None,
    dedupe: str,
    only_actions: tuple[str, ...],
    param_recipes: dict[str, ActionRecipe] | None,
    start_index: int,
) -> tuple[list[PreparedCase], NegativeCorpusReport]:
    """The disabled edges of every reachable state, as rejection cases."""
    try:
        from scripts.analyze_complexity import parse_cfg_constants
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import parse_cfg_constants  # type: ignore[no-redef]

    try:
        from scripts.infer_action_params import parse_variables
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from infer_action_params import parse_variables  # type: ignore[no-redef]

    report = NegativeCorpusReport(dedupe_mode=dedupe)
    variables = parse_variables(tla_source)
    constants = {
        name: coerce_cfg_constant(value) for name, value in parse_cfg_constants(cfg_text).items()
    }
    definitions = parse_tla_definitions(tla_source)
    evaluator = GuardEvaluator(definitions, constants, variables)
    signatures, rejected = extract_action_signatures(
        definitions, evaluator, resolve_next_relation(cfg_text, definitions)
    )
    report.suppressed.update(rejected)

    if only_actions:
        chosen = [name for name in only_actions if name in signatures]
        for name in only_actions:
            if name not in signatures:
                report.suppressed[name] = "named by --negative-action but not a Next disjunct"
        excluded = {name: "not selected by --negative-action" for name in signatures if name not in chosen}
    else:
        chosen, excluded = negatable_actions(signatures, evaluator)
    report.excluded = excluded
    # The variables an excluded action writes are the ones a refusal reports on.
    # Derived from the model rather than named by hand: a module that spells its
    # refusals out has just told the generator which of its variables carry an
    # outcome, and a module that does not gets an empty tuple and the stronger
    # assertion.
    outcome_fields = tuple(
        sorted(
            set().union(
                *(
                    written_variables(signatures[name], evaluator.variables, definitions)
                    for name in excluded
                    if name in signatures
                )
            )
            if excluded
            else set()
        )
    )
    report.outcome_fields = outcome_fields

    chosen = [
        name
        for name in chosen
        if should_emit_action(action_metadata_for(name, view, action_metadata), view)
    ]

    # CROSS-CHECK, run before anything is emitted. Every enabled edge in the
    # dump whose arguments were fully recovered is evaluated at its own source
    # state; the guard of a transition TLC took must not evaluate FALSE. A
    # failure means this evaluator disagrees with TLC, so the action is dropped
    # from the negated set rather than trusted -- the corpus never states
    # something the checker itself has just been shown to get wrong.
    for name in list(chosen):
        failures = 0
        checked = 0
        signature = signatures[name]
        # `CA-06-DF-02`, second face, and the one nobody read. `params_for_case`
        # returns the names the MODULE declares while `signature.params` are the
        # formal ones, so on every model that declares an action marker the two
        # key sets never matched and this cross-check silently examined NOTHING.
        # `CA-06`'s own sealed report prints it -- `cross-check: 0 ENABLED
        # edge(s)` over a dump holding 141 of them.
        formal_for = {
            declared: formal
            for formal, declared in declared_param_names(
                signature.body, signature.params, view
            ).items()
        }
        for edge in edges:
            if edge.action != name:
                continue
            params = params_for_case(edge, states[edge.source], states[edge.target], view, param_recipes)
            if not params or unchecked_param_names(params):
                continue
            params = {formal_for.get(key, key): value for key, value in params.items()}
            if set(params) != set(signature.params):
                continue
            checked += 1
            truth, _ = evaluator.evaluate(signature.body, {**states[edge.source], **params})
            if truth is False:
                failures += 1
        report.crosschecked_edges += checked
        if failures:
            report.crosscheck_failures[name] = failures
            report.suppressed[name] = (
                f"{failures} of {checked} ENABLED edges evaluated FALSE against this "
                "evaluator -- the disagreement is with TLC and the action is not negated"
            )
            chosen.remove(name)

    report.negated = tuple(chosen)
    prepared: list[PreparedCase] = []
    seen: set[Any] = set()
    ordered_states = sorted(states, key=lambda node: (len(node), node))
    for name in chosen:
        signature = signatures[name]
        reads = guard_read_variables(signature, evaluator)
        declared = declared_param_names(signature.body, signature.params, view)
        for node in ordered_states:
            state = states[node]
            for combination in itertools.product(*signature.domains):
                report.candidates += 1
                bindings = dict(zip(signature.params, combination))
                truth, witness = evaluator.evaluate(signature.body, {**state, **bindings})
                if truth is not False:
                    report.not_disabled += 1
                    continue
                reason = witness or "disabled"
                if dedupe == "guard-reads":
                    relevant = {
                        variable: state[variable]
                        for variable in sorted(reads)
                        if variable in state and re.search(rf"\b{re.escape(variable)}\b", reason)
                    }
                    signature_key = freeze_for_signature(
                        {"action": name, "params": bindings, "reason": reason, "reads": relevant}
                    )
                    if signature_key in seen:
                        report.deduped_from += 1
                        continue
                    seen.add(signature_key)
                projected = call_state_projector(state_projector, state)
                # `CA-06-DF-02`. The guard above is evaluated on the FORMAL
                # names it is written in; the case carries the names the module
                # DECLARES, which is what every shipped adapter reads.
                arguments = {
                    declared.get(formal, formal): value for formal, value in bindings.items()
                }
                metadata = action_metadata_for(name, view, action_metadata)
                labels = (
                    name,
                    NEGATIVE_LABEL,
                    REJECTED_LABEL,
                    f"rejects:{name}",
                    # Not `params:recovered`: these arguments were ENUMERATED
                    # from the action's own quantifier domains, never recovered
                    # from a state pair. A reader of the corpus must be able to
                    # tell the two provenances apart.
                    "params:enumerated",
                )
                index = start_index + len(prepared)
                prepared.append(
                    PreparedCase(
                        name=f"{case_name(index, name)}_rejected",
                        edge=Edge(source=node, target=node, action=name),
                        before=projected,
                        after=projected,
                        params=dict(arguments),
                        output_value=None,
                        output_expression=(
                            "StateGraphRejection(action={action!r}, params={params}, "
                            "reason={reason!r}, outcome_fields={outcome})".format(
                                action=name,
                                params=py_repr(dict(arguments)),
                                reason=reason,
                                outcome=py_repr(outcome_fields),
                            )
                        ),
                        changes={},
                        labels=labels,
                        metadata=metadata,
                    )
                )
                report.per_action[name] = report.per_action.get(name, 0) + 1
                report.per_reason[reason] = report.per_reason.get(reason, 0) + 1
    report.emitted = len(prepared)
    report.dump_edges_for_negated = sum(1 for edge in edges if edge.action in set(chosen))
    return prepared, report


def render_negative_report(report: NegativeCorpusReport) -> str:
    lines = [
        "",
        "negative corpus (HP-03): the DISABLED edges of every reachable state, asserted REJECTED",
        f"  emitted:        {report.emitted} case(s) from {report.candidates} candidate (state, action, argument) triples",
        f"  negated:        {', '.join(report.negated) if report.negated else '(none)'}",
    ]
    if report.dedupe_mode != "none":
        lines.append(
            f"  dedupe:         {report.dedupe_mode} collapsed "
            f"{report.emitted + report.deduped_from} -> {report.emitted} "
            "(identical action, arguments, violated conjunct and every state variable that conjunct reads)"
        )
    lines.append(
        f"  cross-check:    {report.crosschecked_edges} ENABLED edge(s) with fully recovered arguments "
        f"re-evaluated at their own source state; {sum(report.crosscheck_failures.values())} evaluated FALSE"
    )
    lines.append(
        f"  verdicts:       {report.emitted + report.deduped_from} proved DISABLED, "
        f"{report.not_disabled} NOT PROVED DISABLED (guards hold, or a conjunct was unevaluable)"
    )
    if report.not_disabled > report.dump_edges_for_negated:
        lines.append(
            f"  NOTE: the dump holds {report.dump_edges_for_negated} edge(s) for these actions while "
            f"{report.not_disabled} argument tuples were not proved disabled -- at least "
            f"{report.not_disabled - report.dump_edges_for_negated} (state, action, argument) triples "
            "have no edge of their own. A DOT dump carries one edge per (source, target, action) and "
            "collapses arguments that agree on the successor. That is why the disabled set is computed "
            "by evaluating the model and NOT by subtracting the dump's edges: the subtraction would "
            "report collapsed-but-enabled inputs as refusable, which is the one error this mode "
            "may not make."
        )
    lines.append(
        "  outcome fields: "
        + (", ".join(report.outcome_fields) if report.outcome_fields else "(none -- full inertness asserted)")
        + " -- variables a refusal legitimately writes, taken from the write set of this "
        "module's own refusal actions; an adapter reports these unobservable and every other "
        "variable is asserted unchanged"
    )
    for action, count in sorted(report.per_action.items()):
        lines.append(f"    {action}: {count}")
    for reason, count in sorted(report.per_reason.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"    reason `{reason}`: {count}")
    for action, why in sorted(report.excluded.items()):
        lines.append(f"  NOT negated: {action} -- {why}")
    for action, why in sorted(report.suppressed.items()):
        lines.append(f"  SUPPRESSED:  {action} -- {why}")
    lines.append(
        "  A suppressed or unevaluable action costs COMPLETENESS, never SOUNDNESS: this mode "
        "emits a case only where the action's own body evaluates to a definite FALSE."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PA-03: ports in the manifest, and cases generated PER PORT
# ---------------------------------------------------------------------------
#
# THE SURFACE COST, stated before the flag was added (plan `surface_cost_rule`).
#
# MODEL DELTA: ZERO. This pass reads `effects.components.<C>.ports.<P>` and
# `effects.actions.<A>` -- a DECLARATION TABLE in the manifest, not TLA+ state.
# No variable, no action, no Next disjunct, no CONSTANT. TLC explores exactly
# the same state graph before and after, so `max_distinct_states` and
# `max_state_space_bound` are untouched and the predecessor's measured ~8x
# state-space cost per surface-adding ticket does not apply here.
#
# WHAT IT COSTS instead is CORPUS SIZE, which is capped, deduped and reported:
# at most one port case per (source case, declared port), and only for actions
# the manifest MAPS. `--port-dedupe region` collapses cases that make the same
# claim. This is a dedupe, never a trim -- both counts are printed.
#
# WHAT IT BUYS: the aspect slice, DERIVED. The hand-authored equivalent in this
# repository's own fixture is a `case_modules:` stanza, a second `.tla`, a
# `.cfg` and a hand-written state projector per slice. A declared port produces
# the same shape from the declaration alone -- plus the two things a slice has
# no way to express: which actions must DRIVE the port and which must LEAVE IT
# ALONE.

PORT_MODES = ("off", "with-positive", "only")
PORT_DEDUPE_MODES = ("none", "region")

#: Every port case carries `port:<component>.<name>` plus exactly one of these.
#: `emitted` means the manifest declares this action on this port; `silent`
#: means the manifest MAPS this action and does not name the port. An action
#: the manifest does not mention at all gets NEITHER -- "we checked, there are
#: none" and "nobody looked" are different claims and this pass never blurs them.
PORT_EMITTED_LABEL = "port-expect:emitted"
PORT_SILENT_LABEL = "port-expect:silent"


@dataclass(frozen=True)
class PortDeclaration:
    """One port an agent declared in the manifest, in the effect-port shape."""

    component: str
    name: str
    attributes: dict[str, Any]
    actions: tuple[str, ...]

    @property
    def qualified(self) -> str:
        return f"{self.component}.{self.name}"

    @property
    def label(self) -> str:
        return f"port:{self.qualified}"


@dataclass(frozen=True)
class PortCatalog:
    """The manifest's port declarations, as the toolchain sees them.

    THE SHIPPED BUILDER (plan `declaration_executability_rule`). Every consumer
    -- this generator, its tests, and the adapter binding PA-04 adds -- reads
    the declarations through this one function, so renaming a port in the
    manifest fails a test instead of silently orphaning the declaration.
    """

    ports: tuple[PortDeclaration, ...]
    #: action -> the qualified ports it declares. An action ABSENT from this
    #: mapping is unmapped; an action present with an empty tuple has been
    #: checked and performs no distinct declared effect.
    mapped_actions: dict[str, tuple[str, ...]]
    source: str

    def ports_for(self, action: str) -> tuple[str, ...]:
        return self.mapped_actions.get(action, ())

    def is_mapped(self, action: str) -> bool:
        return action in self.mapped_actions

    @property
    def dead_ports(self) -> tuple[str, ...]:
        """Declared, and named by no action. REPORTED, never refused."""
        return tuple(port.qualified for port in self.ports if not port.actions)


def load_port_catalog(manifest_path: Path | str | None) -> PortCatalog:
    """Read `effects.components.*.ports` and `effects.actions` from a manifest.

    Deliberately shape-tolerant about a port's ATTRIBUTES. This repository's own
    manifest declares `type` + `target` (the sandbox-observable effect shape);
    the A/B fixture declares `kind` + `description` + `asserts_content`. Both are
    ports under `effects.components.<C>.ports.<P>`, which is the shape the ticket
    asks an agent to declare into, and neither vocabulary is privileged here --
    the attributes travel onto the case as data.
    """
    if manifest_path is None:
        return PortCatalog(ports=(), mapped_actions={}, source="(no manifest)")
    path = Path(manifest_path)
    if not path.is_file():
        return PortCatalog(ports=(), mapped_actions={}, source=f"{path} (missing)")
    manifest = load_manifest(path)
    effects = manifest.get("effects") or {}
    components = effects.get("components") or {}
    raw_actions = effects.get("actions") or {}
    mapped: dict[str, tuple[str, ...]] = {}
    declared_names: dict[str, list[str]] = {}
    for component in sorted(components):
        block = components.get(component) or {}
        for name in sorted((block.get("ports") or {})):
            declared_names.setdefault(name, []).append(component)
    for action in sorted(raw_actions):
        named = raw_actions.get(action) or []
        if isinstance(named, str):
            named = [named]
        qualified: list[str] = []
        for entry in named:
            for component in declared_names.get(str(entry), []):
                qualified.append(f"{component}.{entry}")
        mapped[action] = tuple(sorted(set(qualified)))
    ports: list[PortDeclaration] = []
    for component in sorted(components):
        block = components.get(component) or {}
        for name, attributes in sorted((block.get("ports") or {}).items()):
            qualified = f"{component}.{name}"
            ports.append(
                PortDeclaration(
                    component=component,
                    name=name,
                    attributes=dict(attributes or {}),
                    actions=tuple(
                        action for action in sorted(mapped) if qualified in mapped[action]
                    ),
                )
            )
    return PortCatalog(ports=tuple(ports), mapped_actions=mapped, source=str(path))


def _signatures_for_regions(
    tla_source: str, cfg_text: str
) -> tuple[dict[str, ActionSignature], tuple[str, ...], dict[str, TlaDefinition]]:
    """Parse the module once, the same way the negative pass does.

    Shared deliberately: the write sets a port region is derived from and the
    guards the negative corpus negates must come from ONE reading of ONE module,
    or the two passes can describe different actions.
    """
    try:
        from scripts.analyze_complexity import parse_cfg_constants
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from analyze_complexity import parse_cfg_constants  # type: ignore[no-redef]
    try:
        from scripts.infer_action_params import parse_variables
    except ImportError:  # direct-script import, where sys.path[0] is scripts/
        from infer_action_params import parse_variables  # type: ignore[no-redef]

    variables = parse_variables(tla_source)
    constants = {
        name: coerce_cfg_constant(value) for name, value in parse_cfg_constants(cfg_text).items()
    }
    definitions = parse_tla_definitions(tla_source)
    evaluator = GuardEvaluator(definitions, constants, variables)
    signatures, _ = extract_action_signatures(
        definitions, evaluator, resolve_next_relation(cfg_text, definitions)
    )
    return signatures, variables, definitions


def port_regions(
    catalog: PortCatalog,
    signatures: dict[str, ActionSignature],
    variables: tuple[str, ...],
    definitions: dict[str, TlaDefinition] | None,
) -> tuple[dict[str, frozenset[str]], dict[str, str]]:
    """The modeled variables that lie BEHIND each declared port.

    ``region(P)`` is the set of variables written by some action that declares
    ``P``, minus every variable written by a MAPPED action that does not. A
    variable both sides write is not behind the port -- it is shared, and an
    assertion over it says nothing about the boundary.

    Derived from the model and the declaration together, never named by hand:
    the point of the ticket is that a port an agent invented becomes a port the
    toolchain knows about, and a region the operator has to type again is a
    second declaration to drift from the first.

    UNMAPPED actions are excluded from BOTH sides of the subtraction. An action
    the manifest never mentions has not been checked, and letting it shrink a
    region would let silence narrow an assertion.
    """
    writes: dict[str, frozenset[str]] = {
        name: written_variables(signature, variables, definitions)
        for name, signature in signatures.items()
    }
    regions: dict[str, frozenset[str]] = {}
    reasons: dict[str, str] = {}
    for port in catalog.ports:
        mine: set[str] = set()
        for action in port.actions:
            mine |= writes.get(action, frozenset())
        theirs: set[str] = set()
        for action in sorted(catalog.mapped_actions):
            if action in port.actions:
                continue
            theirs |= writes.get(action, frozenset())
        region = frozenset(mine - theirs)
        regions[port.qualified] = region
        if not port.actions:
            reasons[port.qualified] = (
                "declared by no action in `effects.actions` -- DEAD declared surface, "
                "reported and not refused"
            )
        elif not mine:
            reasons[port.qualified] = (
                "no action declaring this port writes any modeled variable -- the port's "
                "effect is outside the model, so this pass has nothing to assert"
            )
        elif not region:
            reasons[port.qualified] = (
                "every variable its actions write is also written by a mapped action that "
                "does NOT declare this port -- nothing lies behind this boundary in the model"
            )
    return regions, reasons


@dataclass
class PortCorpusReport:
    """Everything the port pass measured. Printed, never summarized away."""

    mode: str = "off"
    dedupe_mode: str = "region"
    manifest: str = ""
    emitted: int = 0
    deduped_from: int = 0
    source_cases: int = 0
    #: qualified port -> {"region": [...], "emitted": n, "silent": n,
    #:                    "per_action": {...}, "attributes": {...}}
    per_port: dict[str, dict[str, Any]] = field(default_factory=dict)
    skipped_ports: dict[str, str] = field(default_factory=dict)
    dead_ports: tuple[str, ...] = ()
    unmapped_actions: tuple[str, ...] = ()
    #: Declaration checked against the MODEL's own write behaviour, both ways.
    #: `pair_cases` is the denominator: a disagreement count with no denominator
    #: cannot be told apart from a whole action disagreeing.
    pair_cases: dict[str, int] = field(default_factory=dict)
    undeclared_region_writes: dict[str, int] = field(default_factory=dict)
    declared_but_inert: dict[str, int] = field(default_factory=dict)


def port_cases_for_corpus(
    *,
    source_cases: list[PreparedCase],
    catalog: PortCatalog,
    regions: dict[str, frozenset[str]],
    skipped: dict[str, str],
    dedupe: str,
    start_index: int,
) -> tuple[list[PreparedCase], PortCorpusReport]:
    """One case set PER DECLARED PORT, derived from the cases already prepared.

    COMPOSITION, not replacement. This pass is a FUNCTION OF the corpus the
    positive and negative passes produced: give it a negative corpus and it
    yields the port's refusal cases, give it both and it yields both, and the
    source cases themselves are emitted unchanged and in their original order.
    That is why `--port-cases` cannot regress the negative corpus -- it does not
    touch it.

    A port case keeps the source case's WHOLE ``before`` (an adapter has to be
    able to build the state at all) and narrows ``after`` to the port's own
    region, which is the same mechanism a hand-authored aspect slice uses and
    the shipped runner already honors field by field.
    """
    report = PortCorpusReport(dedupe_mode=dedupe, source_cases=len(source_cases))
    report.dead_ports = catalog.dead_ports
    report.skipped_ports = dict(skipped)
    prepared: list[PreparedCase] = []
    seen: set[Any] = set()
    unmapped: set[str] = set()
    live_ports = [
        port
        for port in catalog.ports
        if regions.get(port.qualified) and port.qualified not in skipped
    ]
    for port in live_ports:
        report.per_port[port.qualified] = {
            "region": sorted(regions[port.qualified]),
            "attributes": dict(port.attributes),
            "declared_actions": list(port.actions),
            "emitted": 0,
            "silent": 0,
            "cases": 0,
            "per_action": {},
        }
    for case in source_cases:
        action = case.edge.action
        if not catalog.is_mapped(action):
            unmapped.add(action)
            continue
        declared = set(catalog.ports_for(action))
        refused = NEGATIVE_LABEL in case.labels
        for port in live_ports:
            region = regions[port.qualified]
            drives = port.qualified in declared
            after = {name: value for name, value in case.after.items() if name in region}
            before = {name: value for name, value in case.before.items() if name in region}
            moved = before != after
            if dedupe == "region":
                key = freeze_for_signature(
                    {
                        "port": port.qualified,
                        "action": action,
                        "expect": drives,
                        "params": case.params,
                        "before": before,
                        "after": after,
                        "output": case.output_expression,
                        "negative": NEGATIVE_LABEL in case.labels,
                    }
                )
                if key in seen:
                    report.deduped_from += 1
                    continue
                seen.add(key)
            labels = list(case.labels)
            for extra in (port.label, PORT_EMITTED_LABEL if drives else PORT_SILENT_LABEL):
                if extra not in labels:
                    labels.append(extra)
            index = start_index + len(prepared)
            suffix = "_rejected" if NEGATIVE_LABEL in case.labels else ""
            slug = re.sub(r"[^a-z0-9]+", "_", port.qualified.lower()).strip("_")
            prepared.append(
                PreparedCase(
                    name=f"{case_name(index, action)}__port_{slug}{suffix}",
                    edge=case.edge,
                    before=case.before,
                    after=after,
                    params=dict(case.params),
                    output_value=case.output_value,
                    output_expression=case.output_expression,
                    changes={
                        name: change
                        for name, change in case.changes.items()
                        if name in region
                    },
                    labels=tuple(labels),
                    metadata=case.metadata,
                )
            )
            block = report.per_port[port.qualified]
            block["cases"] += 1
            block["emitted" if drives else "silent"] += 1
            per_action = block["per_action"]
            per_action[action] = per_action.get(action, 0) + 1
            # The declaration, checked against the model's own write behaviour,
            # every run and in both directions. Counted AFTER the dedupe so every
            # number in this report shares one denominator, and reported as
            # counts rather than as a refusal: this pass ships no gate (plan
            # `no_new_gates_rule`).
            #
            # A REFUSED call is exempt from the second direction and only from
            # the second. "Declared this port and did not touch it" is exactly
            # what a rejection is SUPPOSED to look like, and counting those as
            # disagreements made every negative case in the A/B fixture report
            # one -- 26 of them, all correct behaviour. "Touched a port it does
            # not declare" stays a disagreement on a refused call, and is the
            # stronger one: a call the model refuses moved the region behind a
            # boundary nobody declared for it.
            pair = f"{action} -> {port.qualified}"
            report.pair_cases[pair] = report.pair_cases.get(pair, 0) + 1
            if moved and not drives:
                report.undeclared_region_writes[pair] = (
                    report.undeclared_region_writes.get(pair, 0) + 1
                )
            if drives and not moved and not refused:
                report.declared_but_inert[pair] = report.declared_but_inert.get(pair, 0) + 1
    report.emitted = len(prepared)
    report.unmapped_actions = tuple(sorted(unmapped))
    return prepared, report


def render_port_report(report: PortCorpusReport) -> str:
    lines = [
        "",
        "port corpus (PA-03): one case set PER DECLARED PORT, from the manifest's own effect-port shape",
        f"  manifest:       {report.manifest}",
        f"  mode:           {report.mode}; source cases {report.source_cases}",
        f"  emitted:        {report.emitted} port case(s)",
    ]
    if report.dedupe_mode != "none":
        lines.append(
            f"  dedupe:         {report.dedupe_mode} collapsed "
            f"{report.emitted + report.deduped_from} -> {report.emitted} "
            "(identical port, action, expectation, arguments, and the port region before and after) "
            "-- a DEDUPE, never a trim"
        )
    if not report.per_port:
        lines.append("  ports:          (none with a modeled region)")
    for qualified, block in sorted(report.per_port.items()):
        lines.append(
            f"    {qualified}: {block['cases']} case(s) "
            f"({block['emitted']} emitted, {block['silent']} silent); "
            f"region {{{', '.join(block['region'])}}}; "
            f"declared by {', '.join(block['declared_actions']) or '(nobody)'}"
        )
        for action, count in sorted(block["per_action"].items()):
            lines.append(f"      {action}: {count}")
    for qualified, why in sorted(report.skipped_ports.items()):
        lines.append(f"  NO CASES:       {qualified} -- {why}")
    if report.dead_ports:
        lines.append(
            "  DEAD DECLARED:  "
            + ", ".join(report.dead_ports)
            + " -- declared under `effects.components` and named by no action"
        )
    if report.unmapped_actions:
        lines.append(
            "  UNMAPPED:       "
            + ", ".join(report.unmapped_actions)
            + " -- absent from `effects.actions`, so no port case is emitted for them. "
            "ABSENT means unmapped; an EMPTY list means checked and no distinct effect."
        )
    for pair, count in sorted(report.undeclared_region_writes.items()):
        lines.append(
            f"  DISAGREEMENT:   {pair} -- {count} of {report.pair_cases.get(pair, 0)} case(s) "
            "change this port's region while the manifest does not declare the port on that action"
        )
    for pair, count in sorted(report.declared_but_inert.items()):
        lines.append(
            f"  DISAGREEMENT:   {pair} -- {count} of {report.pair_cases.get(pair, 0)} accepted "
            "case(s) declare this port and leave its region unchanged"
        )
    lines.append(
        "  A DISAGREEMENT is a finding to read, never a refused build: this pass ships no gate. "
        "It is the declaration checked against the model's own write behaviour, both directions, "
        "every run."
    )
    return "\n".join(lines)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the generation arguments.

    RC-01 (MF-026 G-6). Split out of ``main()`` so `tla-spec-dev generate
    cases` can register the SAME arguments rather than a second, drifting copy.
    Until that ticket the whole of case-module generation was reachable only by
    running this file directly: `build_parser` in scripts/tla_spec_dev.py never
    referenced it, so an import-closure walk of the shipped CLI never saw the
    java spawn at scripts/generate_cases_from_tlc_dump.py:130
    (subprocess.run), the metadir delete at
    scripts/generate_cases_from_tlc_dump.py:154 (shutil.rmtree), the package
    writes at scripts/generate_cases_from_tlc_dump.py:1233 (path.write_text)
    or the parameter-recovery audit write. Nothing generated a case for it,
    nothing adapted it, nothing mutated it, and all four oracles reported green
    over surface the model did not contain.

    RC-02 (MF-026 round-3 N-3). The three citations above each pointed one
    line too high when RC-01 shipped them -- lines 115, 139 and 881-882 for
    code on 116, 140 and 882-883 -- stale in the commit that wrote them, and
    the third consecutive ticket to ship a stale internal citation. They are now file-qualified and content-anchored:
    tests/test_source_citations.py resolves every citation in this repository's
    in-model source, reads the cited line, and fails unless the parenthesised
    anchor is on it. A line shift now breaks a test instead of a reader.
    """
    parser.add_argument("tla", type=Path)
    parser.add_argument("cfg", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help=(
            "Output ROOT for the generated package. An absolute path is used as "
            "given. A RELATIVE path is resolved against the SPEC DIRECTORY (the "
            ".tla's own directory), not the current directory -- unless it already "
            "points inside the spec directory. `--out generated` run from a repo "
            "root therefore writes <spec dir>/generated, which is rarely what was "
            "meant; the resolved root is printed before generation starts. Pass an "
            "absolute path when you want cwd-relative behavior. RC-02: the "
            "RESOLVED path must fall under a `specs/` directory -- that is the "
            "tree the `spec_tree` port declares for this action -- and a path "
            "outside it is refused rather than silently relocated."
        ),
    )
    parser.add_argument(
        "--module-path",
        action="append",
        type=Path,
        default=[],
        metavar="DIR",
        help=(
            "Directory to search for the modules this .tla EXTENDS, ahead of the "
            "directories beside it. Repeatable. TLC resolves EXTENDS against the "
            ".tla's own directory and the TLA-Library search path -- never against "
            "the current directory -- so a case module in specs/case_modules/ that "
            "extends a view in specs/program_model/ needs the view's directory on "
            "this path. Sibling directories of the .tla that contain .tla files are "
            "searched automatically, so the documented layout needs no flag; use "
            "this when the view is somewhere else or when two siblings define the "
            "same module."
        ),
    )
    parser.add_argument("--package", default="tlc_state_graph_cases")
    parser.add_argument("--view", choices=sorted(SUPPORTED_VIEWS), help="Generate a view-aware case package.")
    parser.add_argument("--actions-metadata", type=Path, help="YAML file with actions.<ActionName> layer/controllability/generates.")
    parser.add_argument("--tlc2", default="tlc2")
    parser.add_argument(
        "--dot",
        type=Path,
        help=(
            "Where TLC dumps the state graph. Defaults to <out>/<module>.dot. "
            "RC-02: constrained the same way as --out, and for a stronger "
            "reason -- run_tlc_dump derives the TLC metadir from this path's "
            "parent and `shutil.rmtree`s it in its finally branch, so an "
            "unconstrained --dot is a destructive delete at a caller-chosen "
            "location declared by a port targeting `**/specs/**`."
        ),
    )
    parser.add_argument(
        "--state-projector",
        help=(
            "Optional module:function, or path/to/file.py:function, that projects raw "
            "TLC states before rendering cases. Use the file form for a ticket's own "
            "projector: ticket ids carry dashes, so it has no dotted module name."
        ),
    )
    parser.add_argument(
        "--output-projector",
        help=(
            "Optional module:function, or path/to/file.py:function, that derives "
            "adapter expected output from a TLC transition."
        ),
    )
    parser.add_argument(
        "--dedupe",
        choices=["none", "projected"],
        default="none",
        help="Optionally collapse duplicate projected transitions.",
    )
    parser.add_argument(
        "--labeler",
        action="append",
        default=[],
        help="Optional module:function returning extra labels for before/action/after/changed",
    )
    parser.add_argument(
        "--no-infer-params",
        action="store_true",
        help=(
            "Emit params={} instead of recovering action arguments from each case's "
            "before/after state pair. The MF-029 revert switch: parameter inference is "
            "experimental and generator-side, so turning it off must not require a "
            "model or spec change."
        ),
    )
    parser.add_argument(
        "--negative-cases",
        choices=list(NEGATIVE_MODES),
        default="off",
        help=(
            "HP-03. Also emit, per reachable state, the actions whose guards are "
            "DISABLED there -- one case per refusable argument tuple, asserting the "
            "call is REJECTED and that no modeled variable changes. `with-positive` "
            "appends them to the ordinary corpus; `only` emits the negative corpus "
            "alone, which is how the class is measured on its own. Off by default: "
            "this changes what a corpus contains, and a mode that silently doubled "
            "every existing corpus would be a schedule change nobody asked for."
        ),
    )
    parser.add_argument(
        "--negative-dedupe",
        choices=list(NEGATIVE_DEDUPE_MODES),
        default="guard-reads",
        help=(
            "How negative cases are collapsed. `guard-reads` keeps one case per "
            "(action, arguments, violated conjunct, and every state variable that "
            "conjunct reads) -- cases agreeing on all four are the same test. "
            "`none` keeps one case per reachable state, which is exact and very "
            "large. This is a DEDUPE, never a trim: no case is dropped for fitting "
            "a budget, and the collapsed count is reported either way."
        ),
    )
    parser.add_argument(
        "--negative-action",
        action="append",
        default=[],
        metavar="ACTION",
        help=(
            "Negate exactly these actions, overriding the automatic selection. "
            "By default an action is negated when it writes a variable some guard "
            "reads -- which excludes actions that MODEL a refusal, because the "
            "complement of a refusal is an acceptance and asserting it rejected "
            "would be a false rejection. Repeatable."
        ),
    )
    parser.add_argument(
        "--port-cases",
        choices=list(PORT_MODES),
        default="off",
        help=(
            "PA-03. Also emit one case set PER PORT declared in the manifest under "
            "`effects.components.<C>.ports.<P>`, with `effects.actions` saying which "
            "actions drive which port. A port case narrows the assertion to the port's "
            "own REGION -- the variables written only by actions that declare it -- and "
            "says whether the action must DRIVE the port or LEAVE IT ALONE. "
            "`with-positive` appends the port sets to whatever the positive and negative "
            "passes produced; `only` emits the port sets alone. Off by default, for the "
            "same reason `--negative-cases` is: this changes what a corpus contains."
        ),
    )
    parser.add_argument(
        "--port-dedupe",
        choices=list(PORT_DEDUPE_MODES),
        default="region",
        help=(
            "How port cases are collapsed. `region` keeps one case per (port, action, "
            "expectation, arguments, and the port region before and after) -- cases "
            "agreeing on all of those make the same claim about the boundary. `none` "
            "keeps one per source case. A DEDUPE, never a trim: both counts are printed."
        ),
    )
    parser.add_argument(
        "--port-manifest",
        type=Path,
        help=(
            "Read port declarations from this manifest instead of the one resolved "
            "beside the module. Useful when a case module extends a view whose manifest "
            "is the one carrying the declarations."
        ),
    )
    parser.add_argument(
        "--coverage-json",
        type=Path,
        help=(
            "Also write the aggregated case-module coverage report here, as JSON. "
            "RC-01: the path MUST resolve inside the generated package root -- the "
            "report is an artifact OF the corpus it describes, and the "
            "`spec_tree` port that declares this action's writes covers the "
            "generated tree, not an arbitrary destination."
        ),
    )


def run(args: argparse.Namespace) -> int:
    tla_path = resolve_existing_from_cwd(args.tla)
    spec_dir = resolve_spec_dir(args.tla)
    cfg_path = resolve_existing_spec_input(args.cfg, spec_dir)
    if not cfg_path.exists():
        raise SystemExit(f"ERROR: config not found: {cfg_path} (spec directory: {spec_dir})")
    view = args.view or "internal"
    # RC-02 (MF-026 round-3 N-2): both caller-controlled generation paths are
    # constrained to the tree the `spec_tree` / `spec_tree_delete` ports
    # declare. Resolution itself is unchanged (resolve_spec_tree_out still
    # resolves through resolve_spec_relative_path); what is new is that a path
    # resolving outside a `specs/` directory is REFUSED instead of written to.
    # The metadir `rmtree` in run_tlc_dump's finally branch is derived from
    # `dot_path.parent`, so constraining `--dot` constrains the destructive
    # delete by construction rather than by a second, separate check.
    try:
        out_path = resolve_spec_tree_out(args.out, spec_dir, flag="--out")
        dot_path = (
            resolve_spec_tree_out(args.dot, spec_dir, is_file=True, flag="--dot")
            if args.dot
            else None
        )
    except SpecTreePathError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.view is not None:
        out_path = out_path / VIEW_OUTPUT_DIRS[view]
    if dot_path is None:
        dot_path = out_path / f"{tla_path.stem}.dot"
    report_out_resolution(args.out, out_path, spec_dir)

    for root in [Path.cwd(), Path(__file__).resolve().parents[1], spec_dir]:
        resolved = str(root.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

    # EV-02-DF-02: resolve the EXTENDS hierarchy BEFORE anything expensive runs,
    # so a module that extends a view in another directory either gets that
    # directory on the search path or gets one sentence saying which module is
    # missing and where it was looked for -- not a SANY AbortException stack
    # underneath a complexity paragraph about a bound that could not be measured.
    search_path = resolve_module_search_path(tla_path, args.module_path)
    manifest_path = case_modules.resolve_manifest_path(spec_dir, search_path)

    # Complexity scan (MF-011, made advisory in MF-036). Runs BEFORE
    # run_tlc_dump only so the warnings and recommendations print ahead of the
    # TLC exploration. It never refuses generation -- complexity is advisory.
    advise_complexity(tla_path, cfg_path, spec_dir, search_path)

    run_tlc_dump(tla_path, cfg_path, dot_path, args.tlc2, search_path)
    states, edges = load_dot(dot_path)
    if not states:
        raise SystemExit(f"ERROR: no states parsed from {dot_path}")
    try:
        action_metadata = load_action_metadata(args.actions_metadata, spec_dir)
    except ValueError as error:
        # A malformed actions.yml is an OPERATOR error, and the message already
        # says what to write. A traceback buries it under a stack the operator
        # cannot act on.
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    # MF-029: recover action arguments from each case's own state pair. The
    # recipes come from the SAME module TLC just explored, so the recovery and
    # the corpus can never describe different actions.
    param_recipes = (
        None if args.no_infer_params else build_recipes_for_hierarchy(tla_path, search_path)
    )

    negative_mode = getattr(args, "negative_cases", "off")
    port_mode = getattr(args, "port_cases", "off")
    projector_description = args.state_projector or "none"
    negative_reports: list[NegativeCorpusReport] = []
    port_reports: list[PortCorpusReport] = []
    # PA-03: the manifest is already resolved above -- the SAME one the case cap
    # and the coverage report read, so a port declaration, a budget and a corpus
    # can never be talking about different projects.
    port_manifest_path = getattr(args, "port_manifest", None) or manifest_path
    catalog = load_port_catalog(port_manifest_path) if port_mode != "off" else None
    needs_module_text = negative_mode != "off" or port_mode != "off"
    prepared = render_python_package(
        module=tla_path.stem,
        states=states,
        edges=edges,
        package_dir=out_path / args.package,
        view=view,
        action_metadata=action_metadata,
        labelers=[load_object(path) for path in args.labeler],
        state_projector=load_object(args.state_projector) if args.state_projector else None,
        output_projector=load_object(args.output_projector) if args.output_projector else None,
        dedupe=args.dedupe,
        param_recipes=param_recipes,
        negative=negative_mode,
        negative_dedupe=getattr(args, "negative_dedupe", "guard-reads"),
        negative_actions=tuple(getattr(args, "negative_action", []) or ()),
        tla_source=tla_path.read_text(encoding="utf-8") if needs_module_text else None,
        cfg_text=cfg_path.read_text(encoding="utf-8") if needs_module_text else None,
        projector_description=projector_description,
        negative_report_out=negative_reports,
        ports=port_mode,
        port_dedupe=getattr(args, "port_dedupe", "region"),
        port_catalog=catalog,
        port_report_out=port_reports,
    )
    print(f"spec directory: {spec_dir}")
    print(f"generated {view} cases from {len(states)} states into {out_path / args.package}")
    # RC-02-DF-04: say what shaped the corpus, every run, unprompted. A count
    # whose projection is unnamed cannot be compared with the next one.
    print(f"state projection: {projector_description}; transition dedupe: {args.dedupe}")
    for negative_report in negative_reports:
        print(render_negative_report(negative_report))
    for port_report in port_reports:
        print(render_port_report(port_report))

    # An undeclared zero-case action fails the RUN, not just a log line. The
    # record is already on disk when this raises, so the evidence of why is
    # readable. Caught here rather than propagating a traceback: the operator
    # needs the remedy, and the remedy is in the message.
    try:
        coverage_record = report_action_coverage(
            prepared,
            module=tla_path.stem,
            view=view,
            action_metadata=action_metadata,
            package_dir=out_path / args.package,
            manifest_path=manifest_path,
        )
    except ZeroCaseActionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3

    if getattr(args, "coverage_json", None) is not None:
        write_case_module_coverage_report(
            coverage_record,
            manifest_path=manifest_path,
            view=view,
            action_metadata=action_metadata,
            package_dir=out_path / args.package,
            destination=args.coverage_json,
        )

    if param_recipes is not None:
        # Negative cases are excluded from the recovery audit on purpose: their
        # arguments were ENUMERATED from the quantifier domains, not recovered
        # from a state pair. Counting them would inflate the recovery rate with
        # arguments recovery never touched -- the exact kind of number RP-02
        # was retracted over.
        report_param_recovery(
            [case for case in prepared if NEGATIVE_LABEL not in case.labels],
            param_recipes,
            out_path / args.package,
        )

    # Case-cap hard gate (MF-014). Runs AFTER the complete package is written:
    # the corpus is never trimmed to pass, so the artifacts on disk hold every
    # generated case whether this gate passes or fails. Over cap it reports the
    # distribution and what varies across the redundant group, then exits
    # nonzero -- fix the diagram, or raise the cap with a recorded rationale.
    enforce_case_cap(
        prepared,
        view=view,
        manifest_path=manifest_path,
        source=str(out_path / args.package),
    )
    return 0


def write_case_module_coverage_report(
    coverage_record: dict[str, Any],
    *,
    manifest_path: Path,
    view: str,
    action_metadata: dict[str, ActionMetadata],
    package_dir: Path,
    destination: Path,
) -> Path:
    """Aggregate the case-module coverage report for the corpus just written.

    RC-01 (MF-026 G-6). ``scripts/case_modules.py`` shipped a standalone
    ``main()`` whose ``coverage`` subcommand built this report and wrote it as
    JSON, and NOTHING in `build_parser` reached it. The aggregation is the
    epic's flagship reporting artifact, so it is reachable from the shipped CLI
    here, on the generation path that produces the corpora it reads.

    The destination is required to resolve inside the generated package root:
    the `spec_tree` port declares this action's writes over the generated tree,
    and an unconstrained destination would be the same undeclared-write defect
    the audit filed as G-2/G-3 against the three `--out` flags.
    """
    package_dir = package_dir.resolve()
    resolved = Path(destination).expanduser()
    resolved = (
        resolved.resolve() if resolved.is_absolute() else (Path.cwd() / resolved).resolve()
    )
    if not is_relative_to(resolved, package_dir):
        raise SystemExit(
            f"ERROR: --coverage-json must resolve inside the generated package "
            f"({package_dir}); got {resolved}. The report describes that corpus and is "
            "declared as a write to it.\n"
            f"REMEDY: pick a name INSIDE that package other than "
            f"`{case_modules.COVERAGE_FILENAME}`, which the per-action record already "
            f"owns -- e.g. {package_dir / 'case_module_report.json'}."
        )
    # E-04 (#312): this run writes TWO reports with DIFFERENT schemas, and until
    # now both could land on `case_coverage.json` -- the per-action record
    # (`actions`, `declared_view_actions`, `declared_zero_actions`) and the
    # case-module report (`view_actions`, `uncovered_actions`, `per_action`).
    # The second silently overwrote the first and BOTH printed a success line.
    #
    # Worse, the refusal above steered callers into it: the only path an agent
    # knew inside the package was the one already written, so following the
    # remedy destroyed the report the tool had just produced. A refusal whose
    # remedy causes data loss is worse than no refusal, because it is obeyed in
    # good faith and answers with a confident success.
    if resolved.name == case_modules.COVERAGE_FILENAME:
        raise SystemExit(
            f"ERROR: --coverage-json may not be `{case_modules.COVERAGE_FILENAME}`; got "
            f"{resolved}.\n"
            "That filename is owned by the per-action coverage record this run also "
            "writes, and the two carry DIFFERENT schemas -- writing both here means the "
            "case-module report silently destroys the per-action one, and both report "
            "success.\n"
            f"REMEDY: choose another name inside the package, e.g. "
            f"{resolved.with_name('case_module_report.json')}."
        )
    declared_for_view = {
        name for name, meta in action_metadata.items() if should_emit_action(meta, view)
    }
    report = case_modules.build_report(
        manifest_path=manifest_path,
        corpora=[coverage_record],
        view=view,
        view_actions=declared_for_view,
    )
    write(resolved, json.dumps(case_modules.report_payload(report), indent=2, sort_keys=True) + "\n")
    print(f"case-module coverage report written to {resolved}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_cases_from_tlc_dump",
        description="Generate a view-aware spec-unit case package from a TLC state-graph dump.",
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
