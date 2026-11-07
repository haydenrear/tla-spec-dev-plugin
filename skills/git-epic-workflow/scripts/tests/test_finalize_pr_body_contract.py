"""Doc contract (#200): the epic PR-body template writes one `Closes #N` per line.

GitHub honours only the first issue of `Closes #1, #2, #3`, so a template that
joins them leaves every other issue open.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


FINALIZE = Path(__file__).parents[2] / "references" / "finalize.md"


def pr_body_section() -> str:
    text = FINALIZE.read_text(encoding="utf-8")
    start = text.index("## 5. Update the epic PR")
    end = text.index("\n## 6.", start)
    return text[start:end]


class FinalizePrBodyContractTests(unittest.TestCase):
    def test_template_writes_one_closes_per_line(self) -> None:
        blocks = re.findall(r"```text\n(.*?)```", pr_body_section(), re.S)
        lines = [
            line.strip()
            for block in blocks
            for line in block.splitlines()
            if "closes" in line.lower()
        ]
        self.assertGreaterEqual(len(lines), 2, "template shows no Closes lines")
        for line in lines:
            self.assertRegex(line, r"\ACloses #\d+\Z")


if __name__ == "__main__":
    unittest.main()
