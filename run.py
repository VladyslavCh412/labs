"""Compatibility entry point; the complete application lives in lab8final/."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parent/'lab8final'/'run.py'),run_name='__main__')
