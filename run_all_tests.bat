@echo off
REM Windows batch script to run all tests
REM This sets PYTHONPATH and runs pytest

set PYTHONPATH=%CD%
echo Running tests with PYTHONPATH=%PYTHONPATH%
python -m pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO
