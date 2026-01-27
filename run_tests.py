#!/usr/bin/env python
"""
Test runner that ensures proper Python path before running pytest.
This works reliably across all platforms.
"""
import sys
import os
import subprocess

# Set PYTHONPATH environment variable
project_root = os.path.abspath(os.path.dirname(__file__))
env = os.environ.copy()
env['PYTHONPATH'] = project_root

if __name__ == '__main__':
    # Run pytest as a subprocess with PYTHONPATH set
    args = [
        sys.executable,
        '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '-o', 'log_cli=true',
        '-o', 'log_cli_level=INFO'
    ]
    sys.exit(subprocess.call(args, env=env))
