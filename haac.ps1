$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-HaacArch {
    $raw = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
    switch ($raw) {
        "x64" { return "amd64" }
        "arm64" { return "arm64" }
        default { throw "Unsupported Windows architecture for haac: $raw" }
    }
}

function Get-HaacBinaryPath {
    $arch = Get-HaacArch
    return Join-Path $repoRoot ".tools\windows-$arch\bin\haac.exe"
}

function Test-HaacBinaryStale {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BinaryPath
    )

    if (-not (Test-Path $BinaryPath)) {
        return $true
    }

    $binaryTime = (Get-Item $BinaryPath).LastWriteTimeUtc
    $sourcePaths = @(
        (Join-Path $repoRoot "go.mod"),
        (Join-Path $repoRoot "go.sum"),
        (Join-Path $repoRoot "cmd"),
        (Join-Path $repoRoot "internal")
    )

    foreach ($path in $sourcePaths) {
        if (-not (Test-Path $path)) {
            continue
        }
        $item = Get-Item $path
        if ($item.PSIsContainer) {
            $newer = Get-ChildItem $path -Recurse -File | Where-Object { $_.LastWriteTimeUtc -gt $binaryTime } | Select-Object -First 1
            if ($newer) {
                return $true
            }
            continue
        }
        if ($item.LastWriteTimeUtc -gt $binaryTime) {
            return $true
        }
    }

    return $false
}

function Ensure-HaacBinary {
    $binary = Get-HaacBinaryPath
    if ((Test-Path $binary) -and -not (Test-HaacBinaryStale -BinaryPath $binary)) {
        return $binary
    }

    $go = Get-Command go -ErrorAction SilentlyContinue
    if (-not $go) {
        throw "Repo-local haac binary not found at '$binary' and Go is unavailable. Install Go or build cmd/haac first."
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $binary) | Out-Null
    & $go.Source build -o $binary .\cmd\haac
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $binary)) {
        throw "Failed to build repo-local haac binary at '$binary'."
    }
    return $binary
}

Push-Location $repoRoot
try {
    foreach ($arg in $args) {
        if ($arg -like "internal:*") {
            Write-Error "internal:* Task targets are not part of the supported haac operator surface; use a public task instead"
        }
    }

    $haac = Ensure-HaacBinary
    & $haac @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
