---
type: regex
pattern: 'worktree_parent_dir|outermost|gitlink|160000'
weight: 2
---

THE REASON, WHICH IS THE HALF THAT IS EASY TO MISS. Naming `integration.toml`
can be luck — the word `constituent` is in the prompt and one grep finds the
marker. What this grader scores is the agent getting to WHY the rule exists:

  * `worktree_parent_dir()` — the function, at
    `skills/git-issue-workflow/scripts/lib.sh:341 (worktree_parent_dir)`, which
    returns `dirname` of the outermost enclosing integration root;
  * **outermost**, not nearest: integration repos nest, and it is the outermost
    working tree that must stay unpolluted;
  * the consequence the rule prevents: a linked worktree's `.git` is a FILE, so
    a parent `git add -A` stages the whole directory as a **gitlink** (mode
    `160000`) — a submodule in all but name, which `INTEGRATION.md` rule 1
    forbids — and no `.gitignore` glob can separate `constituents/foo-TICKET`
    from a real constituent named `foo`.

Any one of those four spellings passes. All four are absent from the prompt.

An agent that answers "skt put it in the wrong place" scores zero here and
should: the command is correct, and the defect is in the node's fixture, which
builds its throwaway repo INSIDE an integration repository and then asserts a
path that can never be right there.
