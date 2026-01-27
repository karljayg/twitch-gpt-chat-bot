#!/bin/bash
# Set PYTHONPATH to project root to fix import issues
export PYTHONPATH="$(pwd):$PYTHONPATH"
python -m pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO
