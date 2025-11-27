#!/usr/bin/env python3
"""
Quick syntax check and test runner for the codebase.
Run this before committing to catch syntax errors and test failures.

Usage:
    python check_code.py              # Run with verbose logging (default)
    python check_code.py --quiet      # Run with minimal output
"""
import sys
import subprocess
import ast
import os
import argparse
from pathlib import Path

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error in {file_path}:{e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error checking {file_path}: {e}"

def find_python_files(directory='.'):
    """Find all Python files in the directory"""
    python_files = []
    base_path = Path(directory).resolve()
    for root, dirs, files in os.walk(directory):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'env', '.pytest_cache', 'node_modules', 'logs', 'data', 'temp', 'sounds']]
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                # Convert to relative path
                rel_path = os.path.relpath(full_path, base_path)
                python_files.append(rel_path)
    return python_files

def main():
    parser = argparse.ArgumentParser(description='Check code syntax and run tests')
    parser.add_argument('--quiet', '-q', action='store_true', 
                       help='Run with minimal output (no verbose logging)')
    args = parser.parse_args()
    
    # Immediate output to confirm script is running
    import sys
    sys.stdout.flush()
    
    print("=" * 60)
    print("Code Quality Check")
    print("=" * 60)
    sys.stdout.flush()
    
    # Step 1: Syntax check
    print("\n[1/2] Checking syntax...")
    errors = []
    python_files = find_python_files()
    
    # Focus on core and handlers (most critical)
    critical_dirs = ['core', 'adapters', 'api', 'tests']
    critical_files = [f for f in python_files if any(f.replace('\\', '/').startswith(d + '/') or f.replace('\\', '/').startswith(d + '\\') for d in critical_dirs)]
    
    print(f"Checking {len(critical_files)} critical files...")
    for file_path in critical_files:
        is_valid, error = check_syntax(file_path)
        if not is_valid:
            errors.append(error)
            print(f"  [ERROR] {error}")
    
    if errors:
        print(f"\n[FAIL] Found {len(errors)} syntax error(s)!")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    print("  [OK] All syntax checks passed")
    
    # Step 2: Run tests
    print("\n[2/2] Running tests...")
    try:
        # Build pytest command
        pytest_cmd = [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short']
        
        # Add verbose logging by default (unless --quiet flag)
        if not args.quiet:
            pytest_cmd.extend(['-o', 'log_cli=true', '-o', 'log_cli_level=INFO'])
        
        result = subprocess.run(
            pytest_cmd,
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"\n[FAIL] Tests failed with exit code {result.returncode}")
            return 1
        print("\n[OK] All tests passed")
        return 0
    except Exception as e:
        print(f"\n[FAIL] Error running tests: {e}")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Check cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

