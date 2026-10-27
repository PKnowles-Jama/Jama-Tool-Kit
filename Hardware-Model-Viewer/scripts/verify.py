"""Run checks in the selected Python environment and stop on the first failure."""
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for args in (['-m','unittest','discover','-s','tests','-p','test_*.py','-q'],
             ['tests/browser_check.py'],['tests/browser_integration.py']):
    subprocess.run([sys.executable,*args],cwd=ROOT,check=True)
print('All local unit and browser checks passed.')
