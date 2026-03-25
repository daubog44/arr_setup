$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction Stop

& $python.Source (Join-Path $repoRoot "scripts/haac.py") task-run -- @args
exit $LASTEXITCODE
