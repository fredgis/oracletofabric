[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SubscriptionId,

    [Parameter(Mandatory)]
    [string]$TenantId,

    [string]$ResourceGroupName = 'FGI-ORACLE',
    [switch]$RunCdcValidation
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$statePath = "$env:LOCALAPPDATA\OracleToFabricDemo\state.json"

function Unprotect-LocalValue {
    param([string]$Value)

    return [System.Net.NetworkCredential]::new('', (ConvertTo-SecureString $Value)).Password
}

function Get-FabricContext {
    param([pscustomobject]$State)

    $token = (az account get-access-token `
        --subscription $State.subscriptionId `
        --resource 'https://api.fabric.microsoft.com' `
        --output json | ConvertFrom-Json).accessToken
    $headers = @{ Authorization = "Bearer $token" }
    $workspace = (Invoke-RestMethod -Headers $headers -Uri 'https://api.fabric.microsoft.com/v1/workspaces').value |
        Where-Object displayName -eq 'FGI-ORACLE' |
        Select-Object -First 1
    return @{
        Token = $token
        Headers = $headers
        Workspace = $workspace
    }
}

$identityExisted = $false
if (Test-Path -LiteralPath $statePath) {
    $initialState = Get-Content -Raw $statePath | ConvertFrom-Json
    $identityExisted = [bool]$initialState.gatewayIdentity.appId
}

& (Join-Path $PSScriptRoot 'Deploy-DemoFoundation.ps1') `
    -SubscriptionId $SubscriptionId `
    -TenantId $TenantId `
    -ResourceGroupName $ResourceGroupName

& (Join-Path $PSScriptRoot 'Initialize-DemoIdentity.ps1') `
    -SubscriptionId $SubscriptionId `
    -TenantId $TenantId

if (-not $identityExisted) {
    & (Join-Path $PSScriptRoot 'Deploy-DemoFoundation.ps1') `
        -SubscriptionId $SubscriptionId `
        -TenantId $TenantId `
        -ResourceGroupName $ResourceGroupName
}

$state = Get-Content -Raw $statePath | ConvertFrom-Json
$oracleInstallScript = Join-Path $repoRoot 'oracle\Install-OracleDemo.sh'
$oracleRpmUrl = 'https://download.oracle.com/otn-pub/otn_software/db-free/oracle-ai-database-free-26ai-23.26.3-1.el9.x86_64.rpm'
$oracleRpmSha256 = '895fc9df794685b515c4ac83f104dbdfb657eb0e92c41e45c58302fb8fd53e44'

az vm run-command invoke `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroupName `
    --name $state.oracleVmName `
    --command-id RunShellScript `
    --scripts "@$oracleInstallScript" `
    --parameters $state.keyVaultName $oracleRpmUrl $oracleRpmSha256 `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'Oracle installation failed.'
}

$fabric = Get-FabricContext -State $state
$gateways = (Invoke-RestMethod -Headers $fabric.Headers -Uri 'https://api.fabric.microsoft.com/v1/gateways').value
$gateway = $gateways |
    Where-Object displayName -eq 'Demo Oracle Gateway' |
    Select-Object -First 1

if (-not $gateway) {
    $clientSecret = Unprotect-LocalValue -Value $state.gatewayIdentity.protectedClientSecret
    $recoveryKey = Unprotect-LocalValue -Value $state.protected.gatewayRecoveryKey
    $commandName = 'demo-register-gateway'
    az vm run-command delete `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroupName `
        --vm-name $state.gatewayVmName `
        --run-command-name $commandName `
        --yes `
        --output none 2>$null
    az vm run-command create `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroupName `
        --vm-name $state.gatewayVmName `
        --run-command-name $commandName `
        --location $state.location `
        --script "@$(Join-Path $repoRoot 'fabric\Register-DemoGateway.ps1')" `
        --protected-parameters "ClientSecret=$clientSecret" "RecoveryKey=$recoveryKey" `
        --parameters `
            "ApplicationId=$($state.gatewayIdentity.appId)" `
            "TenantId=$TenantId" `
            'GatewayName=Demo Oracle Gateway' `
            'RegionKey=centralus' `
        --timeout-in-seconds 300 `
        --async-execution false `
        --output none
    $registrationExitCode = $LASTEXITCODE
    az vm run-command delete `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroupName `
        --vm-name $state.gatewayVmName `
        --run-command-name $commandName `
        --yes `
        --output none
    $cleanupExitCode = $LASTEXITCODE
    if ($registrationExitCode -ne 0) {
        throw 'Gateway registration failed.'
    }
    if ($cleanupExitCode -ne 0) {
        throw 'Gateway registration succeeded, but its temporary Run Command could not be removed.'
    }

    $gateway = (Invoke-RestMethod -Headers $fabric.Headers -Uri 'https://api.fabric.microsoft.com/v1/gateways').value |
        Where-Object displayName -eq 'Demo Oracle Gateway' |
        Select-Object -First 1
    if (-not $gateway) {
        throw 'Gateway registration completed but the gateway is not visible in Fabric.'
    }
}

$gatewayRoles = (Invoke-RestMethod `
    -Headers $fabric.Headers `
    -Uri "https://api.fabric.microsoft.com/v1/gateways/$($gateway.id)/roleAssignments").value
if (-not ($gatewayRoles | Where-Object { $_.principal.id -eq $state.gatewayIdentity.servicePrincipalId })) {
    Invoke-RestMethod `
        -Headers $fabric.Headers `
        -Uri "https://api.fabric.microsoft.com/v1/gateways/$($gateway.id)/roleAssignments" `
        -Method Post `
        -ContentType 'application/json' `
        -Body (@{
            principal = @{
                id = $state.gatewayIdentity.servicePrincipalId
                type = 'ServicePrincipal'
            }
            role = 'Admin'
        } | ConvertTo-Json -Depth 5) | Out-Null
}

& (Join-Path $repoRoot 'fabric\Configure-DemoFabric.ps1') -SubscriptionId $SubscriptionId
& (Join-Path $repoRoot 'tests\Validate-AzureDemo.ps1') -SubscriptionId $SubscriptionId

$state = Get-Content -Raw $statePath | ConvertFrom-Json
$oracleValidation = az vm run-command invoke `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroupName `
    --name $state.oracleVmName `
    --command-id RunShellScript `
    --scripts "@$(Join-Path $repoRoot 'oracle\Validate-OracleDemo.sh')" `
    --query 'value[0].message' `
    --output tsv
$oracleValidationText = $oracleValidation -join "`n"
if ($oracleValidationText -notmatch 'FACT_SALES=25000') {
    throw "Oracle validation failed: $oracleValidationText"
}

$keyVaultValidation = az vm run-command invoke `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroupName `
    --name $state.oracleVmName `
    --command-id RunShellScript `
    --scripts "@$(Join-Path $repoRoot 'oracle\Validate-KeyVaultSecrets.sh')" `
    --parameters $state.keyVaultName `
    --query 'value[0].message' `
    --output tsv
$keyVaultValidationText = $keyVaultValidation -join "`n"
if ($keyVaultValidationText -notmatch 'demo-gateway-app-client-secret\|STATUS=present') {
    throw "Key Vault validation failed: $keyVaultValidationText"
}

if ($RunCdcValidation) {
    & (Join-Path $repoRoot 'tests\Invoke-DemoCdcValidation.ps1')
}

Write-Output 'DEMO_DEPLOYMENT_VALID=true'
