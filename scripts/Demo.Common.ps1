function Assert-DemoCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Remediation
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required.`nRun:`n$Remediation"
    }
}

function Invoke-DemoNativeCommand {
    param(
        [Parameter(Mandatory)]
        [scriptblock]$Command,

        [Parameter(Mandatory)]
        [string]$Description
    )

    $stderrPath = Join-Path $env:TEMP "oracle-fabric-stderr-$([guid]::NewGuid().ToString('N')).txt"
    try {
        $output = @(& $Command 2> $stderrPath)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            $stderr = if (Test-Path -LiteralPath $stderrPath) {
                Get-Content -Raw $stderrPath
            }
            else {
                ''
            }
            $details = ((@($output) + @($stderr)) | Out-String).Trim()
            throw "$Description failed with exit code $exitCode.`n$details"
        }
        return $output
    }
    finally {
        if (Test-Path -LiteralPath $stderrPath) {
            Remove-Item -LiteralPath $stderrPath -Force
        }
    }
}

function Get-DemoExactNameCount {
    param(
        [Parameter(Mandatory)]
        [scriptblock]$ListCommand,

        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Description
    )

    $json = (Invoke-DemoNativeCommand -Command $ListCommand -Description $Description) -join "`n"
    try {
        $resources = $json | ConvertFrom-Json
    }
    catch {
        throw "$Description returned invalid JSON."
    }
    return @($resources | Where-Object name -eq $Name).Count
}

function Get-DemoJwtClaims {
    param(
        [Parameter(Mandatory)]
        [string]$AccessToken
    )

    $payload = $AccessToken.Split('.')[1].Replace('-', '+').Replace('_', '/')
    switch ($payload.Length % 4) {
        2 { $payload += '==' }
        3 { $payload += '=' }
    }
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) |
        ConvertFrom-Json
}

function Get-DemoClientCredentialToken {
    param(
        [Parameter(Mandatory)]
        [string]$TenantId,

        [Parameter(Mandatory)]
        [string]$ClientId,

        [Parameter(Mandatory)]
        [string]$ClientSecret,

        [Parameter(Mandatory)]
        [string]$Resource
    )

    $scope = "$($Resource.TrimEnd('/'))/.default"
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body @{
            client_id = $ClientId
            client_secret = $ClientSecret
            grant_type = 'client_credentials'
            scope = $scope
        }
    return $response.access_token
}

function Get-DemoSqlCmdInstallCommand {
    return 'winget install --id Microsoft.Sqlcmd --exact --accept-source-agreements --accept-package-agreements --silent'
}
