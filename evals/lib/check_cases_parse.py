"""Does every `case.yaml` PARSE? Say so by name before the corpus is scored.

WHY THIS EXISTS (#389, found by SI-22 as `SI-22-DF-08`). When a `case.yaml`
fails to parse, `claude plugin eval` prints one line -- `1 case file(s) failed
to load` -- somewhere in the middle of a run, and the corpus count silently
drops by one. The table that follows looks completely normal. Nothing in the
summary, the totals, or the exit code says a case is missing, and nothing names
WHICH case went missing.

IT ALREADY HAPPENED HERE, AND THE EPIC AGENT MERGED IT.
`evals/spec-double-2/w-sdc-spec-unit-ticket-runs-only-the-first-target/case.yaml`
was measured by SI-21 at 1.00 on 6/6 runs, twice. Then SI-21's FINAL commit
(`eeb352f9`) added a prose block and cost the file its two-space indent. Proved
by parsing the file at each commit, with a non-vacuity control:

    c96de147 .. ac195c6e   2475 bytes   LOADS
    eeb352f9               3162 bytes   ScannerError, line 22   <-- SI-21's last commit
    58463ebe               3162 bytes   ScannerError            <-- the epic merge
    872b3b30               3164 bytes   LOADS                   <-- SI-22 fixed it

The case's measured 1.00 was honest -- it loaded when it was measured -- and it
had not run since. The epic agent verified that merge four ways (ancestry, graph
assertions from fresh summary.json, suite failure names, and that the new check
exits 0) and NONE of those touch whether a shipped case file still parses.

WHY A PRE-FLIGHT AND NOT A BETTER READING OF THE RUNNER'S OUTPUT. The runner's
line arrives mid-run, after the money is committed, without a filename, and the
corpus total it changes is never stated as an expectation -- so 57 of 58 reads
exactly like 58 of 58. Parsing the files costs nothing and needs no billing.

WHAT IT IS NOT. Not a gate. `GOAL-no-new-gates` is live and SI-23 decides it:
this PRINTS AND EXITS 0, always -- including when it finds unparseable files,
and including when it cannot run at all. A corpus short by one should still
run. It should just be unable to do so quietly.

NON-VACUITY. A checker that scans nothing reports "0 unparseable" and looks
identical to a clean corpus -- the exact shape of the bug it is checking for,
and a mistake this epic has already shipped once (`find` on an absent directory
reporting "ok, no symlinks"). So it asserts it found a plausible number of case
files and says how many it scanned, every time, even when all is well.

WHY IT OBTAINS PyYAML INSTEAD OF ASSUMING IT (`SI-29-DF-03`, CORRECTED).
The first version simply imported `yaml` and printed, when that failed:

    cases: SKIPPED -- PyYAML is not importable here, so no case file was parsed.

SI-29 reported that as a high-severity inert check: `run.sh` invoking a `python3`
without PyYAML, so nothing was ever parsed. **That claim does not hold on this
machine, and the epic agent repeated it before checking.** `run.sh` is a bash
script, and in a non-interactive bash `python3` resolves to `/usr/bin/python3`,
which HAS PyYAML. Verified by running the original file through bash exactly as
line 269 does: `cases: 70 case file(s) parse.` The SKIPPED line both of us saw
came from an INTERACTIVE zsh carrying `alias python3=python`, and an alias does
not exist inside a script. So the check was working where it runs.

What survives the correction is a portability hole and a wording bug, and both
are worth the code below. On any host whose `/usr/bin/python3` lacks PyYAML --
most Linux images, most containers, most CI -- the original would have gone
quiet, and this lane's whole subject is checks that fail quietly. And "SKIPPED"
was the wrong word: a line a reader mistakes for a non-failure is how such a
thing survives. The warning now says the corpus is UNVERIFIED and never says
skipped.

So the dependency is obtained rather than assumed: the module RE-EXECS itself
through `uv` (already a hard dependency of this lane -- `run.sh` stages wheels
with it), measured at 135ms warm, and warns loudly only if even that is
impossible.

Worth keeping in view: the other four `evals/lib` checkers import nothing beyond
the standard library. This one needs a YAML parser to do its job at all, so it
cannot follow that convention -- it can only make the dependency its own problem
instead of the caller's.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

#: Set in the re-exec'd child so a broken uv environment cannot loop.
_REEXEC_GUARD = "SKT_CASES_PARSE_REEXEC"

#: Below this, assume the scan is broken rather than the corpus tiny. The
#: corpus was 70 files at 82015294; a real corpus never shrinks by an order of
#: magnitude, but a bad root silently yields zero.
MIN_PLAUSIBLE_CASES = 10


def _load_yaml():
    """yaml, or None. Missing PyYAML is a fact about the host, not a failure."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return None
    return yaml


def find_case_files(root: Path) -> list[Path]:
    """Every `<unit>/<case>/case.yaml` under the eval root, sorted."""
    return sorted(root.glob("*/*/case.yaml"))


def check(root: Path) -> tuple[int, list[tuple[Path, str]]]:
    """Returns (files scanned, [(path, why)]) for everything that will not load."""
    yaml = _load_yaml()
    if yaml is None:
        return 0, []
    files = find_case_files(root)
    bad: list[tuple[Path, str]] = []
    for f in files:
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - any parse failure is the finding
            first = str(exc).replace("\n", " ")[:120]
            bad.append((f, f"{type(exc).__name__}: {first}"))
            continue
        if not isinstance(doc, dict):
            bad.append((f, f"parsed as {type(doc).__name__}, not a mapping"))
    return len(files), bad


def _reexec_through_uv(argv: list[str]) -> int | None:
    """Re-run this module under a uv environment that HAS PyYAML.

    Returns the child's exit code, or None when no re-exec was possible — the
    caller then warns rather than reporting a clean corpus. Guarded by an
    environment variable so a uv that cannot supply yaml fails once, not
    forever.
    """
    if os.environ.get(_REEXEC_GUARD):
        return None
    uv = shutil.which("uv")
    if uv is None:
        return None
    env = dict(os.environ, **{_REEXEC_GUARD: "1"})
    cmd = [uv, "run", "--quiet", "--python", "3.12", "--with", "pyyaml",
           "python", str(Path(__file__).resolve()), *argv[1:]]
    try:
        return subprocess.run(cmd, env=env, timeout=120).returncode
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    if _load_yaml() is None:
        # Obtain the dependency rather than assume it. SI-29-DF-03, corrected:
        # this branch is NOT reached under `run.sh` on the development machine
        # (bash resolves /usr/bin/python3, which has PyYAML). It is reached on a
        # host whose system python lacks it, and the first version went quiet
        # there -- which is the portability hole worth closing.
        rc = _reexec_through_uv(argv)
        if rc is not None:
            return rc
        print(
            "cases: WARNING -- NO case file was checked. PyYAML is not importable "
            f"under {sys.executable} and this could not re-run itself through uv. "
            "An unparseable case.yaml would drop out of the corpus silently and the "
            "run would still look clean (#389). Treat the corpus as UNVERIFIED."
        )
        return 0

    scanned, bad = check(root)

    if scanned < MIN_PLAUSIBLE_CASES:
        # The non-vacuity arm. Never silent: a scan that found nothing is a
        # broken scan, and reporting "0 unparseable" would be the bug itself.
        print(
            f"cases: WARNING -- scanned only {scanned} case file(s) under {root}, "
            f"fewer than the {MIN_PLAUSIBLE_CASES} expected. Treat this checker as "
            "not having run; it is looking in the wrong place."
        )
        return 0

    if not bad:
        print(f"cases: {scanned} case file(s) parse.")
        return 0

    print(
        f"cases: WARNING -- {len(bad)} of {scanned} case file(s) WILL NOT LOAD. "
        "Each one drops out of the corpus silently and the run still looks clean (#389):"
    )
    for path, why in bad:
        try:
            shown = path.relative_to(root)
        except ValueError:
            shown = path
        print(f"  {shown}")
        print(f"    {why}")
    print(
        f"  the corpus will score {scanned - len(bad)}, not {scanned}. "
        "Nothing is refused -- fix the file or expect a short corpus."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
