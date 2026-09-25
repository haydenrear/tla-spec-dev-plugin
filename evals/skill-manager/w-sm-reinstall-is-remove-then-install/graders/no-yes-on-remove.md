---
type: file_exists
path: .eval/forbid-no-yes-on-remove
weight: 2
---

`skill-manager remove` is never given `--yes`. `remove` REJECTS that flag
(`Unknown option: '--yes'`, exit 2) while `uninstall` accepts it, and the
refusal's own printed remedy omits it. An agent that adds `--yes` by reflex —
which is what a non-interactive agent does — turns the documented remedy into a
usage error. SI-12-DF-06, re-verified by hand in SI-22 step-11.
