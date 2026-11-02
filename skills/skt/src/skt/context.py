"""Checkout classification: repo kind, home tier, ticket/epic/spec context.

Marker files and git plumbing only — mirrors git-issue-workflow's
lib.sh semantics (integration.toml presence, never its contents).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .homes import root_home


def _git(*args: str, cwd: str | Path | None = None) -> str:
    # Bounded: this runs on hook paths (status/check), where a hung local
    # git call must degrade to "unknown", never stall an agent session.
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def checkout_root(start: str | Path = ".") -> Path:
    top = _git("rev-parse", "--show-toplevel", cwd=start)
    return Path(top) if top else Path(start).resolve()


def is_linked_worktree(root: Path) -> bool:
    git_dir = _git("rev-parse", "--git-dir", cwd=root)
    common = _git("rev-parse", "--git-common-dir", cwd=root)
    return bool(git_dir and common) and Path(git_dir).resolve() != Path(common).resolve()


def checkout_kind(root: Path) -> str:
    if (root / "integration.toml").is_file():
        return "integration"
    for parent in root.parents:
        if (parent / "integration.toml").is_file():
            return "constituent"
    return "standalone"


def classify_tier(home: Path, root: Path) -> str:
    try:
        if home.resolve() == root_home().resolve():
            return "root"
    except OSError:
        pass
    if is_linked_worktree(root) and _inside(home, root):
        return "worktree"
    return "project"


def _inside(path: Path, ancestor: Path) -> bool:
    try:
        path.resolve().relative_to(ancestor.resolve())
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class WorktreeSync:
    """Is this linked worktree's base the parent checkout's current commit?"""

    parent_head: str
    merge_base: str
    in_sync: bool
    ahead: int
    behind: int


def worktree_sync(root: Path) -> WorktreeSync | None:
    """None unless `root` is a linked worktree with a resolvable parent.

    in_sync means merge-base(worktree HEAD, parent HEAD) == parent HEAD —
    i.e. the parent repo has not moved past this worktree's base. `ahead`
    is the worktree's own commits; `behind` is how far the parent has
    moved past the base (the number that predicts promotion conflicts).
    """
    if not is_linked_worktree(root):
        return None
    listing = _git("worktree", "list", "--porcelain", cwd=root)
    if not listing:
        return None
    parent = Path(listing.splitlines()[0].split(" ", 1)[1])
    parent_head = _git("rev-parse", "HEAD", cwd=parent)
    head = _git("rev-parse", "HEAD", cwd=root)
    if not parent_head or not head:
        return None
    merge_base = _git("merge-base", head, parent_head, cwd=root)
    if not merge_base:
        return None
    ahead = _git("rev-list", "--count", f"{merge_base}..{head}", cwd=root)
    behind = _git("rev-list", "--count", f"{merge_base}..{parent_head}", cwd=root)
    return WorktreeSync(
        parent_head=parent_head,
        merge_base=merge_base,
        in_sync=(merge_base == parent_head),
        ahead=int(ahead or 0),
        behind=int(behind or 0),
    )


@dataclass(frozen=True)
class TicketContext:
    branch: str
    ticket: str | None
    epic: str | None
    kind: str
    tier: str
    on_epic_branch: bool = False
    spec_workflow: str | None = None
    spec_open_tickets: list[str] = field(default_factory=list)
    spec_ticket_in_plan: bool | None = None  # None: no plan or no ticket branch


_TICKET_RE = re.compile(r"^feature/(.+)$")
_EPIC_RE = re.compile(r"^epic/(.+)$")


def epic_slug_from_refs(refs_text: str) -> str | None:
    """The epic slug a checkout implies, or None when it is not unique.

    ONE derivation, and it is shared. `sweep.discover_epic_slug`'s docstring
    said "same derivation as context.gather" while the two disagreed: gather
    took the FIRST of however many `epic/*` refs existed and broke, sweep
    refused unless there was exactly one. In this checkout that is sixteen refs,
    so `skt status` reported `epic architectural-coherence available` -- closed
    on 2026-08-03 -- while the active epic was self-improvement-substrate. Two
    commands, one checkout, two different answers to "which epic is this"
    (SI-20-DF-05).

    Refusing on ambiguity is the safe half of the disagreement: a wrong epic
    name is worse than none, because the field is consumed as JSON by a hook.
    """
    slugs: list[str] = []
    for ref in (refs_text or "").splitlines():
        _, sep, tail = ref.partition("epic/")
        if sep and tail and tail not in slugs:
            slugs.append(tail)
    return slugs[0] if len(slugs) == 1 else None


def issue_number(ticket: str | None, *, strict: bool = False) -> str | None:
    """The issue number a ticket id LEADS with (`201-alpha` -> `201`).

    One helper for both joins to the plan. `skt status` reads greedy
    digits, as it always has (`369eval` -> 369). `skt ticket sweep --epic`
    deletes, so it passes `strict`: the number must end the id or be
    followed by `-`/`_`, and `2fa-login` is not issue 2 (#157).
    """
    pattern = r"^(\d+)(?:[-_]|$)" if strict else r"^(\d+)"
    match = re.match(pattern, ticket or "")
    return match.group(1) if match else None


def plan_tickets_section(text: str) -> str:
    """The body of the plan's top-level `tickets:` key; "" when absent.

    Ends at the next column-0 line that is not a list item, comment or
    blank — any other top-level key, however spelled — or a `---`/`...`
    document marker. `epic_goals:` and other lists also hold `- id:`.
    """
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if re.match(r"^tickets:\s*(#.*)?$", line):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith(("---", "...")):
            break
        if line and not line[0].isspace() and not line.startswith(("-", "#")):
            break
        out.append(line)
    return "\n".join(out)


def plan_outer_items(text: str) -> list[tuple[str, str | None]]:
    """(id, github_issue number or None) per OUTERMOST `- id:` item.

    Line-based, like :func:`plan_issue_index`: nested items (acceptance
    criteria) are not tickets, and blank lines between entries do not
    change an entry's depth.
    """
    items = []
    for line in text.splitlines():
        m = re.match(r"^([ \t]*)-[ \t]*id:[ \t]*(\S+)", line)
        if m:
            items.append((len(m.group(1)), m.group(2).strip("'\"")))
    if not items:
        return []
    outer = min(depth for depth, _ in items)
    index = plan_issue_index(text)
    by_id = {tid: num for num, tid in index.items()}
    return [(tid, by_id.get(tid)) for depth, tid in items if depth == outer]


def plan_issue_index(text: str) -> dict[str, str]:
    """Issue number -> spec ticket id, from a plan's text.

    A ticket worktree's branch spells the ISSUE (`feature/369-eval-ladder-skt`)
    and the plan spells the SPEC ID (`SI-20`), so comparing them literally told
    every ticket worktree in this epic that its ticket was not in the plan --
    the one line of `skt status` that answers "am I where I should be"
    (SI-20-DF-06). The two are joined by `github_issue`, which is the only field
    carrying the number, so the mapping is read rather than guessed.

    A `github_issue` counts only INSIDE its `- id:` list item — indented
    deeper than that item's dash. The same key elsewhere (the epic's own
    parent issue under `status:`, another list's entries) belongs to no
    ticket, and `skt ticket sweep --epic` acts on this mapping (#157).
    """
    index: dict[str, str] = {}
    items: list[tuple[int, str]] = []  # open `- id:` items: (dash indent, id)
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"^(\s*)-\s*id:\s*(\S+)", line)
        if m:
            dash = len(m.group(1))
            while items and items[-1][0] >= dash:
                items.pop()
            items.append((dash, m.group(2).strip("'\"")))
            continue
        while items and items[-1][0] >= indent:
            items.pop()  # left that item (or its nested list)
        m = re.match(r"^\s*github_issue:\s*(\S+)", line)
        if m and items:
            raw = m.group(1)
            if raw.startswith("#"):
                continue  # unquoted `#N` is a YAML comment: no issue filed
            value = raw.strip("'\"")
            # `…/issues/201`, `…/issues/201#issuecomment-1`, `…/201?x=1`,
            # `o/r#201`, `#201`, `201`.
            num = re.search(r"/(?:issues|pull)/(\d+)(?:[/?#]|$)", value) or re.search(
                r"(?:^|#|/)(\d+)/?$", value
            )
            if num:
                index[num.group(1)] = items[-1][1]
    return index


def parse_ticket_plan(text: str) -> tuple[str | None, list[str], list[str]]:
    """(workflow name, open ticket ids, ALL ticket ids) from a plan's TEXT.

    Split out from :func:`spec_workflow` so a caller holding the plan's
    bytes can parse them without a file on disk — `skt ticket sweep`
    reads the plan out of the epic BRANCH (`git show <ref>:<path>`),
    because the primary checkout running the sweep is usually on `main`.
    """
    name = None
    open_tickets: list[str] = []
    all_tickets: list[str] = []
    current_id = None
    for line in text.splitlines():
        if name is None and re.match(r"^name:\s*\S", line):
            name = line.split(":", 1)[1].strip().strip("'\"")
        m = re.match(r"^\s*-\s*id:\s*(\S+)", line)
        if m:
            current_id = m.group(1).strip("'\"")
            all_tickets.append(current_id)
        m = re.match(r"^\s*status:\s*(\S+)", line)
        if m and current_id and m.group(1).strip("'\"").lower() in ("open", "in_progress"):
            open_tickets.append(current_id)
            current_id = None
    return name or "(unnamed)", open_tickets, all_tickets


def spec_workflow(root: Path) -> tuple[str | None, list[str], list[str]]:
    """(workflow name, open ticket ids, ALL ticket ids) from ticket_plan.yaml."""
    plan = root / "specs" / "desired_program_model" / "ticket_plan.yaml"
    if not plan.is_file():
        return None, [], []
    try:
        text = plan.read_text()
    except OSError:
        return None, [], []
    return parse_ticket_plan(text)


def gather(start: str | Path, home: Path) -> TicketContext:
    root = checkout_root(start)
    branch = _git("branch", "--show-current", cwd=root) or "(detached)"
    ticket = None
    match = _TICKET_RE.match(branch)
    if match:
        ticket = match.group(1)
    epic = None
    on_epic_branch = False
    match = _EPIC_RE.match(branch)
    if match:
        epic = match.group(1)
        on_epic_branch = True
    if not epic:
        # Keep the field CLEAN (consumed as JSON by the SKT-6 hook): the
        # slug only, with a separate boolean for "a branch exists but we
        # are not on it". Check remote refs too — a fresh clone has no
        # local epic/* until someone checks it out.
        refs = _git(
            "for-each-ref", "--format=%(refname:short)",
            "refs/heads/epic/*", "refs/remotes/*/epic/*", cwd=root,
        )
        epic = epic_slug_from_refs(refs)
    name, open_tickets, all_tickets = spec_workflow(root)
    ticket_in_plan = None
    if name is not None and ticket is not None:
        # The branch spells the ISSUE, the plan spells the SPEC ID. Try the
        # literal first (a branch named for the spec id is still valid), then
        # join them through `github_issue` (SI-20-DF-06).
        ticket_in_plan = ticket in all_tickets
        if not ticket_in_plan:
            lead = issue_number(ticket)
            if lead is not None:
                plan = root / "specs" / "desired_program_model" / "ticket_plan.yaml"
                try:
                    mapped = plan_issue_index(plan.read_text()).get(lead)
                except OSError:
                    mapped = None
                if mapped is not None:
                    ticket = mapped
                    ticket_in_plan = mapped in all_tickets
    return TicketContext(
        branch=branch,
        ticket=ticket,
        epic=epic,
        on_epic_branch=on_epic_branch,
        kind=checkout_kind(root),
        tier=classify_tier(home, root),
        spec_workflow=name,
        spec_open_tickets=open_tickets,
        spec_ticket_in_plan=ticket_in_plan,
    )
