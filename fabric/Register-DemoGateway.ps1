param(
    [Parameter(Mandatory)]
    [string]$ApplicationId,

    [Parameter(Mandatory)]
    [string]$TenantId,

    [Parameter(Mandatory)]
    [string]$ClientSecret,

    [Parameter(Mandatory)]
    [string]$RecoveryKey,

    [string]$GatewayName = 'Demo Oracle Gateway',
    [string]$RegionKey = 'centralus'
)

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) {
    & 'C:\Program Files\PowerShell\7\pwsh.exe' `
        -NoLogo `
        -NoProfile `
        -File $PSCommandPath `
        -ApplicationId $ApplicationId `
        -TenantId $TenantId `
        -ClientSecret $ClientSecret `
        -RecoveryKey $RecoveryKey `
        -GatewayName $GatewayName `
        -RegionKey $RegionKey
    exit $LASTEXITCODE
}

Import-Module DataGateway
Import-Module DataGateway.Profile

$secureClientSecret = ConvertTo-SecureString $ClientSecret -AsPlainText -Force
$secureRecoveryKey = ConvertTo-SecureString $RecoveryKey -AsPlainText -Force

Connect-DataGatewayServiceAccount `
    -ApplicationId $ApplicationId `
    -ClientSecret $secureClientSecret `
    -Tenant $TenantId | Out-Null

try {
    $existing = @(Get-DataGatewayCluster) |
        Where-Object {
            $_.GatewayName -eq $GatewayName -or
            $_.Name -eq $GatewayName -or
            $_.DisplayName -eq $GatewayName
        } |
        Select-Object -First 1

    if (-not $existing) {
        Add-DataGatewayCluster `
            -GatewayName $GatewayName `
            -RecoveryKey $secureRecoveryKey `
            -RegionKey $RegionKey | Out-Null
    }

    Write-Output "GATEWAY_REGISTERED=$GatewayName"
}
finally {
    Disconnect-DataGatewayServiceAccount
}
