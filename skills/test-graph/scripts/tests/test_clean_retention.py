"""Bounded cleanup preserves its existing Python 3.10 import surface."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


class RuntimeCompatibilityTest(unittest.TestCase):
    def test_clean_imports_without_tomllib(self):
        source = """import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
 if name=='tomllib': raise ModuleNotFoundError('no tomllib')
 return original(name,*args,**kwargs)
builtins.__import__=guarded
script=sys.argv.pop(1)
sys.path.insert(0,str(__import__('pathlib').Path(script).parent))
runpy.run_path(script,run_name='__main__')
"""
        process = subprocess.run([sys.executable, '-B', '-c', source, str(SCRIPTS / 'clean.py'), '--help'],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('--retain', process.stdout)

    def test_changed_entrypoints_keep_python_310_syntax(self):
        epic = SCRIPTS.parents[1] / 'git-epic-workflow/scripts'
        for path in [SCRIPTS / 'clean.py', epic / 'milestone.py', epic / 'evidence.py']:
            ast.parse(path.read_text(), feature_version=(3, 10))


if __name__ == '__main__':
    unittest.main()
