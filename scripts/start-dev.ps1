param([ValidateSet('backend', 'frontend')][string]$Service = 'backend')
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDirectory
if ($Service -eq 'backend') {
    $env:DEBUG = 'true'
    & .\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
} else {
    Set-Location -LiteralPath (Join-Path $projectDirectory 'frontend')
    npm run dev
}
