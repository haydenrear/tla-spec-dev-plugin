"""Is there a test_graph project with a REGISTERED graph and a real node?

EXIT CODE ONLY. Run under `checks/nowrite.sb`; the hook writes the verdict.

`test-graph`'s claim is behavioural validation: a DAG of self-describing nodes
that exercises the program the way a user would, rather than another unit test
that asserts the current shape of the code. The cheap failure is a directory
that looks like a scaffold -- a build file, an empty graph, no node -- so the
check requires the three things that make it a graph rather than a folder:

  * the scaffold exists (settings + build files);
  * a graph is REGISTERED by name in the composition;
  * at least one node file exists AND the registered graph refers to it.

Running the graph would be better evidence and is deliberately not attempted:
the node runtime wants Gradle and a JBang or uv toolchain that the eval sandbox
does not reliably have, and a check that cannot run produces the same absent
verdict as work that was never done. What is missing is named in the output so
a reader of a red can tell those apart.

Exit 0  scaffold + a registered graph + a node the graph refers to
Exit 1  anything less
"""

from __future__ import annotations

import os
import pathlib
import re

ROOT = pathlib.Path("test_graph")
NODE_MARKERS = ("NodeResult", "node_result", "nodeResult", "metadata")
#: Never walked. `build/` alone is 1.7M entries in a real checkout, and walking
#: it also invents thousands of duplicate "node files" from compiled copies --
#: which is how a failure message came to list AppRunning.java sixty times.
SKIP_DIRS = {"build", ".gradle", ".git", "node_modules", "__pycache__",
             "venv", ".venv", ".history"}


def main() -> int:
    if not ROOT.is_dir():
        print("no test_graph/ directory")
        return 1

    # ONE PRUNED WALK FOR EVERYTHING. `rglob` here was the real cost: it
    # enumerates `test_graph/build/`, which holds 1,761,027 entries in a real
    # checkout, three times over before any filter runs. Pruning only the node
    # walk left these untouched and the check still timed out.
    build_files, settings, nodes = [], [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            fp = pathlib.Path(dirpath) / fn
            if fn in ("build.gradle.kts", "build.gradle"):
                build_files.append(fp)
            elif fn in ("settings.gradle.kts", "settings.gradle"):
                settings.append(fp)
            elif fn.endswith((".java", ".py", ".kt")):
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if any(m in text for m in NODE_MARKERS):
                    nodes.append(fp)
    build_files.sort(); settings.sort()
    if not build_files:
        print("test_graph/ has no build file, so nothing composes a graph")
        return 1
    if not settings:
        print("test_graph/ has no settings file, so the project is not a project")
        return 1

    composition = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in build_files)

    # A registered graph: the composition names one. Spellings differ between
    # scaffold versions, so several are accepted rather than one pinned.
    graphs = set()
    for pattern in (
        r"testGraph\s*\(\s*[\"']([A-Za-z0-9_-]+)[\"']",
        r"graph\s*\(\s*[\"']([A-Za-z0-9_-]+)[\"']",
        r"register\s*\(\s*[\"']([A-Za-z0-9_-]+)[\"']",
        r"create\s*\(\s*[\"']([A-Za-z0-9_-]+)[\"']",
        r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*\{\s*$",
    ):
        graphs |= set(re.findall(pattern, composition, re.M))
    if not graphs:
        print("the build file registers no graph by name")
        return 1

    if not nodes:
        print(f"a graph is registered ({sorted(graphs)}) but no node file describes itself")
        return 1

    # And the graph has to REFER to a node, or it is an empty declaration beside
    # a file nobody runs.
    node_ids = {p.stem for p in nodes} | {p.stem.replace("_", "-") for p in nodes}
    # THE STEM INSIDE A QUOTED STRING, not the stem as the whole string. The
    # framework spells a reference `node("sources/<stem>.py")` -- a path, with a
    # directory in front and an extension behind -- so a pattern anchored to the
    # quotes matches nothing. Measured against this repository's OWN build file,
    # which composes five graphs that all pass: `"tla_spec_dev_cli_install"`
    # NOT FOUND, while the file plainly contains
    # `node("sources/tla_spec_dev_cli_install.py")`. The check was rejecting the
    # reference implementation, so `compose-a-behavioural-graph` could not be
    # passed by composing a correct graph.
    referred = [
        n for n in node_ids
        if re.search(rf"[\"'][^\"']*(?<![A-Za-z0-9_]){re.escape(n)}(?![A-Za-z0-9_])[^\"']*[\"']",
                     composition)
    ]
    if not referred:
        print(
            f"graphs {sorted(graphs)} refer to none of the node files "
            f"{sorted(p.name for p in nodes)}"
        )
        return 1

    print(f"graph ok: {sorted(graphs)} refers to {sorted(referred)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
