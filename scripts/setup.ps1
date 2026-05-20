# Recreate the Poetry virtualenv with pyenv Python 3.13.
# Close VS Code/Cursor first if removal of .venv fails (Ruff may lock ruff.exe).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Get-Process ruff -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*$Root*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue

if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
}

$py = & pyenv which python
if (-not $py) {
    throw "pyenv Python not found. Install 3.13.0: pyenv install 3.13.0"
}

poetry env use $py
poetry install
poetry env info

Write-Host ""
Write-Host "Setup complete. Run: poetry run uvicorn app.main:app --reload"
