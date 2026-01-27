# PowerShell script to run all tests with proper PYTHONPATH
$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$env:PYTHONPATH = "$ProjectRoot"

Write-Host "Running tests with PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Green
python -m pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO
