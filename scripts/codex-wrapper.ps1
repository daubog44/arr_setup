param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ForwardArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeParent = Join-Path $repoRoot ".codex-appserver-runtime"
$runtimeRoot = Join-Path $runtimeParent ("run-" + [Guid]::NewGuid().ToString("N"))
$codexHome = Join-Path $runtimeRoot ".codex"
$globalHome = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
$repoLocalSkills = Join-Path $repoRoot ".codex\skills"
$configPath = Join-Path $codexHome "config.toml"

New-Item -ItemType Directory -Force -Path $runtimeParent | Out-Null
New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

if (Test-Path $repoLocalSkills -PathType Container) {
  Copy-Item -Recurse -Force $repoLocalSkills (Join-Path $codexHome "skills")
}

foreach ($fileName in @("auth.json", "cap_sid")) {
  $source = Join-Path $globalHome $fileName
  $destination = Join-Path $codexHome $fileName
  if (Test-Path $source -PathType Leaf) {
    Copy-Item -Force $source $destination
  }
}

$configToml = @'
model = "gpt-5.4"
model_reasoning_effort = "xhigh"
personality = "pragmatic"
service_tier = "fast"
sandbox_mode = "danger-full-access"

[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--headless", "--isolated"]

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"

[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_PAT_TOKEN"

[plugins."github@openai-curated"]
enabled = true

[plugins."figma@openai-curated"]
enabled = true
'@

[System.IO.File]::WriteAllText($configPath, $configToml, [System.Text.Encoding]::UTF8)

$env:CODEX_HOME = $codexHome
$env:HOME = $runtimeRoot
$env:USERPROFILE = $runtimeRoot

$codexBinary = (Get-Command codex.cmd -CommandType Application).Source
& $codexBinary @ForwardArgs
exit $LASTEXITCODE
