$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repoRoot 'scripts\Demo.Common.ps1')

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

$missingCommandObserved = $false
try {
    Assert-DemoCommand `
        -Name 'command-that-must-not-exist-oracle-fabric-demo' `
        -Remediation 'install-command'
}
catch {
    if ($_.Exception.Message -notmatch 'install-command') {
        throw
    }
    $missingCommandObserved = $true
}
if (-not $missingCommandObserved) {
    throw 'Missing command did not return its remediation.'
}

$failureCommand = {
    & $pwsh -NoProfile -Command "Write-Output 'ResourceNotFound'; exit 3"
}.GetNewClosure()
$failureObserved = $false
try {
    Get-DemoExactNameCount `
        -ListCommand $failureCommand `
        -Name 'demo-bastion' `
        -Description 'Bastion list test' | Out-Null
}
catch {
    if ($_.Exception.Message -notmatch 'ResourceNotFound') {
        throw
    }
    $failureObserved = $true
}
if (-not $failureObserved) {
    throw 'Native command failure was incorrectly treated as resource output.'
}

$missingCommand = {
    & $pwsh -NoProfile -Command '$data = @(@{ name = "other-bastion" }); $data | ConvertTo-Json -Compress; exit 0'
}.GetNewClosure()
$missingCount = Get-DemoExactNameCount `
    -ListCommand $missingCommand `
    -Name 'demo-bastion' `
    -Description 'Missing Bastion test'
if ($missingCount -ne 0) {
    throw "Expected no exact Bastion match, found $missingCount."
}

$existingCommand = {
    & $pwsh -NoProfile -Command '$data = @(@{ name = "demo-bastion" }); $data | ConvertTo-Json -Compress; exit 0'
}.GetNewClosure()
$existingCount = Get-DemoExactNameCount `
    -ListCommand $existingCommand `
    -Name 'demo-bastion' `
    -Description 'Existing Bastion test'
if ($existingCount -ne 1) {
    throw "Expected one exact Bastion match, found $existingCount."
}

Write-Output 'DEMO_COMMON_TESTS_VALID=true'
