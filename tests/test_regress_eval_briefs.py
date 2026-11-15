"""The w-skt-regress-* agent cases embed the brief `skt regress run` writes.

A copy that has drifted from the code measures a prompt nobody ships (the
stale-prompt finding in specs/results/skt-regress/attribution.yaml).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_eval_briefs_are_the_briefs_the_code_writes():
    proc = subprocess.run([sys.executable, str(ROOT / "evals" / "skt" / "regen_regress_briefs.py"), "--check"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, (
        proc.stdout + proc.stderr + "\nfix: python3 evals/skt/regen_regress_briefs.py")
