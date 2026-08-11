param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$Source = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path ".opencode"
$Target = Join-Path $ProjectRoot ".opencode"

if (-not (Test-Path $Source)) {
    throw "Source .opencode directory not found: $Source"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item -Recurse -Force (Join-Path $Source "*") $Target

Write-Host "Installed SimInspect-X project-local OpenCode runtime to:"
Write-Host "  $Target"
Write-Host ""
Write-Host "Restart/reopen OpenCode in the project. TaskBuilder should appear as a primary agent."
