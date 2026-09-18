$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Create the project virtual environment first.' }

& $python -m pip install 'pyinstaller>=6,<7' 'pystray>=0.19,<1' 'Pillow>=10,<12'
& $python -m PyInstaller --noconfirm --clean --onefile --name MoonRuntime --add-data "$root\frontend;frontend" --collect-all uvicorn --collect-all fastapi --collect-all starlette --collect-all pystray --collect-all PIL "$root\moon_runtime.py"

Write-Host "Runtime created at $root\dist\MoonRuntime.exe"
