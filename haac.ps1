$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$go = Get-Command go -ErrorAction SilentlyContinue

Push-Location $repoRoot
try {
    foreach ($arg in $args) {
        if ($arg -like "internal:*") {
            Write-Error "internal:* Task targets are not part of the supported haac operator surface; use a public task instead"
        }
    }

    if ($go) {
        & $go.Source run .\cmd\haac @args
        if ($LASTEXITCODE -eq 0) {
            exit 0
        }
        Write-Warning "Go/Cobra entrypoint failed; falling back to the Python bridge."
    }

    $python = Get-Command python -ErrorAction Stop
    & $python.Source (Join-Path $repoRoot "scripts/haac.py") task-run -- @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
