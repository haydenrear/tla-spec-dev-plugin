---
type: regex
pattern: 'install-skt\.sh|src/skt/cli\.py'
weight: 2
---

THE SECOND HALF, and the one that separates a diagnosis from a fix. Two answers
are correct and both are scored:

  * run the source directly — `python3 <checkout>/skills/skt/src/skt/cli.py status`
    (skt is stdlib-only by contract, so this needs no venv); or
  * install the checkout's copy INTO a home and run the wrapper that produces:
    copy the unit into `<home>/plugins/<plugin>/`, then run
    `skill-scripts/install-skt.sh` with `SKILL_DIR` pointing into that home.
    That is the only shape a real install has, and it is how the SI-20 gamut
    made the bytes under test equal the bytes under review.

What does NOT pass, and should not: clearing a cache, adjusting `PATH`,
`skill-manager sync skt` (skt is not a standalone unit any more — it is
contained in the `tla-spec-dev` plugin, which is the whole of `GOAL-one-plugin`),
or re-running the same wrapper.
