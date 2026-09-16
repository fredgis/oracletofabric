[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SubscriptionId,

    [string]$WorkspaceName = 'FGI-ORACLE',
    [string]$GatewayName = 'Demo Oracle Gateway',
    [string]$LakehouseName = 'DemoLakehouse',
    [string]$ConnectionName = 'Demo Oracle Connection',
    [string]$MirrorName = 'DemoOracleMirror',
    [string]$OracleServer = '10.60.1.4:1521/FREEPDB1',
    [string]$StatePath = "$env:LOCALAPPDATA\OracleToFabricDemo\state.json"
)

$ErrorActionPreference = 'Stop'
$fabricBaseUri = 'https://api.fabric.microsoft.com/v1'
$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repoRoot 'scripts\Demo.Common.ps1')

function Unprotect-LocalValue {
    param([string]$Value)

    return [System.Net.NetworkCredential]::new('', (ConvertTo-SecureString $Value)).Password
}

function Join-ByteArrays {
    param([byte[][]]$Arrays)

    $length = ($Arrays | Measure-Object -Property Length -Sum).Sum
    $result = New-Object byte[] $length
    $offset = 0
    foreach ($array in $Arrays) {
        [Buffer]::BlockCopy($array, 0, $result, $offset, $array.Length)
        $offset += $array.Length
    }
    return $result
}

function Protect-GatewayBasicCredentials {
    param(
        [string]$Username,
        [string]$Password,
        [string]$Modulus,
        [string]$Exponent
    )

    $credentialJson = @{
        credentialData = @(
            @{ name = 'username'; value = $Username }
            @{ name = 'password'; value = $Password }
        )
    } | ConvertTo-Json -Compress
    $plainText = [Text.Encoding]::UTF8.GetBytes($credentialJson)
    $modulusBytes = [Convert]::FromBase64String($Modulus)
    $exponentBytes = [Convert]::FromBase64String($Exponent)

    if ($modulusBytes.Length -eq 128) {
        $encrypted = [System.Collections.Generic.List[byte]]::new()
        for ($offset = 0; $offset -lt $plainText.Length; $offset += 85) {
            $length = [Math]::Min(85, $plainText.Length - $offset)
            $segment = New-Object byte[] $length
            [Buffer]::BlockCopy($plainText, $offset, $segment, 0, $length)
            $rsa = [Security.Cryptography.RSACryptoServiceProvider]::new()
            try {
                $parameters = $rsa.ExportParameters($false)
                $parameters.Modulus = $modulusBytes
                $parameters.Exponent = $exponentBytes
                $rsa.ImportParameters($parameters)
                $encrypted.AddRange($rsa.Encrypt($segment, $true))
            }
            finally {
                $rsa.Dispose()
            }
        }
        return [Convert]::ToBase64String($encrypted.ToArray())
    }

    $keyEnc = [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    $keyMac = [Security.Cryptography.RandomNumberGenerator]::GetBytes(64)
    $aes = [Security.Cryptography.Aes]::Create()
    try {
        $aes.KeySize = 256
        $aes.Mode = [Security.Cryptography.CipherMode]::CBC
        $aes.Padding = [Security.Cryptography.PaddingMode]::PKCS7
        $aes.Key = $keyEnc
        $encryptor = $aes.CreateEncryptor()
        try {
            $cipherText = $encryptor.TransformFinalBlock($plainText, 0, $plainText.Length)
        }
        finally {
            $encryptor.Dispose()
        }
        $iv = $aes.IV
    }
    finally {
        $aes.Dispose()
    }

    $algorithmChoices = [byte[]](0, 0)
    $tagData = Join-ByteArrays -Arrays @($algorithmChoices, $iv, $cipherText)
    $hmac = [Security.Cryptography.HMACSHA256]::new($keyMac)
    try {
        $tag = $hmac.ComputeHash($tagData)
    }
    finally {
        $hmac.Dispose()
    }
    $authenticatedCipherText = Join-ByteArrays -Arrays @($algorithmChoices, $tag, $iv, $cipherText)

    $keys = New-Object byte[] 98
    $keys[0] = 0
    $keys[1] = 1
    [Buffer]::BlockCopy($keyEnc, 0, $keys, 2, $keyEnc.Length)
    [Buffer]::BlockCopy($keyMac, 0, $keys, 34, $keyMac.Length)

    $rsa = [Security.Cryptography.RSA]::Create()
    try {
        $parameters = [Security.Cryptography.RSAParameters]::new()
        $parameters.Modulus = $modulusBytes
        $parameters.Exponent = $exponentBytes
        $rsa.ImportParameters($parameters)
        $encryptedKeys = $rsa.Encrypt($keys, [Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
    }
    finally {
        $rsa.Dispose()
    }

    return [Convert]::ToBase64String($encryptedKeys) + [Convert]::ToBase64String($authenticatedCipherText)
}

function Invoke-FabricRequest {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body
    )

    $arguments = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        SkipHttpErrorCheck = $true
    }
    if ($null -ne $Body) {
        $arguments.ContentType = 'application/json'
        $arguments.Body = $Body | ConvertTo-Json -Depth 20
    }

    $response = Invoke-WebRequest @arguments
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        if ($response.StatusCode -in 401, 403) {
            throw "Fabric automation identity is not authorized for $Method $Uri. Verify tenant settings, API roles, workspace Contributor, and gateway Admin access."
        }
        throw "Fabric request failed: $Method $Uri returned $($response.StatusCode): $($response.Content)"
    }
    if ([string]::IsNullOrWhiteSpace($response.Content)) {
        return $null
    }
    return $response.Content | ConvertFrom-Json
}

function Find-FabricNamedValue {
    param(
        [string]$Uri,
        [hashtable]$Headers,
        [string]$DisplayName,
        [int]$Attempts = 18,
        [int]$DelaySeconds = 10
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $item = (Invoke-FabricRequest `
            -Method Get `
            -Uri $Uri `
            -Headers $Headers).value |
            Where-Object displayName -eq $DisplayName |
            Select-Object -First 1
        if ($item) {
            return $item
        }
        if ($attempt -lt $Attempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $StatePath)) {
    throw "Deployment state not found: $StatePath"
}

$state = Get-Content -Raw $StatePath | ConvertFrom-Json
$mirrorPassword = Unprotect-LocalValue -Value $state.protected.mirrorPassword

$gatewayClientSecret = Unprotect-LocalValue `
    -Value $state.gatewayIdentity.protectedClientSecret
$fabricToken = Get-DemoClientCredentialToken `
    -TenantId $state.tenantId `
    -ClientId $state.gatewayIdentity.appId `
    -ClientSecret $gatewayClientSecret `
    -Resource 'https://api.fabric.microsoft.com'
$headers = @{ Authorization = "Bearer $fabricToken" }

$workspace = Find-FabricNamedValue `
    -Uri "$fabricBaseUri/workspaces" `
    -Headers $headers `
    -DisplayName $WorkspaceName
if (-not $workspace) {
    throw "Fabric workspace $WorkspaceName was not visible to the automation service principal within three minutes."
}

$gateway = Find-FabricNamedValue `
    -Uri "$fabricBaseUri/gateways" `
    -Headers $headers `
    -DisplayName $GatewayName
if (-not $gateway) {
    throw "Fabric gateway $GatewayName was not visible to the automation service principal within three minutes."
}
$gateway = Invoke-FabricRequest -Method Get -Uri "$fabricBaseUri/gateways/$($gateway.id)" -Headers $headers

$connections = (Invoke-FabricRequest -Method Get -Uri "$fabricBaseUri/connections" -Headers $headers).value
$connection = $connections |
    Where-Object displayName -eq $ConnectionName |
    Select-Object -First 1
if (-not $connection) {
    $encryptedCredentials = Protect-GatewayBasicCredentials `
        -Username 'C##FABRIC_MIRROR' `
        -Password $mirrorPassword `
        -Modulus $gateway.publicKey.modulus `
        -Exponent $gateway.publicKey.exponent

    $connectionBody = @{
        connectivityType = 'OnPremisesGateway'
        gatewayId = $gateway.id
        displayName = $ConnectionName
        connectionDetails = @{
            type = 'Oracle'
            creationMethod = 'Oracle'
            parameters = @(
                @{
                    dataType = 'Text'
                    name = 'server'
                    value = $OracleServer
                }
            )
        }
        privacyLevel = 'Organizational'
        credentialDetails = @{
            singleSignOnType = 'None'
            connectionEncryption = 'NotEncrypted'
            skipTestConnection = $false
            credentials = @{
                credentialType = 'Basic'
                values = @(
                    @{
                        gatewayId = $gateway.id
                        encryptedCredentials = $encryptedCredentials
                    }
                )
            }
        }
    }
    $connection = Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/connections" `
        -Headers $headers `
        -Body $connectionBody
}
if (-not $state.deploymentUserId) {
    throw 'The deploying user object ID is missing from the local deployment state.'
}
Ensure-DemoFabricRoleAssignment `
    -ResourceUri "$fabricBaseUri/connections/$($connection.id)" `
    -Headers $headers `
    -PrincipalId $state.deploymentUserId `
    -PrincipalType User `
    -Role Owner `
    -ResourceDescription $ConnectionName | Out-Null

$items = (Invoke-FabricRequest -Method Get -Uri "$fabricBaseUri/workspaces/$($workspace.id)/items" -Headers $headers).value
$lakehouse = $items |
    Where-Object { $_.type -eq 'Lakehouse' -and $_.displayName -eq $LakehouseName } |
    Select-Object -First 1
if (-not $lakehouse) {
    $lakehouse = Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/lakehouses" `
        -Headers $headers `
        -Body @{
            displayName = $LakehouseName
            description = 'Lakehouse for the Oracle to Fabric Demo'
            creationPayload = @{
                enableSchemas = $true
            }
        }
}

$mirrors = (Invoke-FabricRequest -Method Get -Uri "$fabricBaseUri/workspaces/$($workspace.id)/mirroredDatabases" -Headers $headers).value
$mirror = $mirrors |
    Where-Object displayName -eq $MirrorName |
    Select-Object -First 1
if (-not $mirror) {
    $definition = @{
        properties = @{
            source = @{
                type = 'Oracle'
                typeProperties = @{
                    connection = $connection.id
                    database = 'FREEPDB1'
                }
            }
            target = @{
                type = 'MountedRelationalDatabase'
                typeProperties = @{
                    defaultSchema = 'DEMO_DW'
                    format = 'Delta'
                    retentionInDays = 1
                }
            }
            mountedTables = @(
                'DIM_DATE',
                'DIM_CUSTOMER',
                'DIM_PRODUCT',
                'DIM_STORE',
                'FACT_SALES'
            ) | ForEach-Object {
                @{
                    source = @{
                        typeProperties = @{
                            schemaName = 'DEMO_DW'
                            tableName = $_
                        }
                    }
                }
            }
        }
    }
    $payload = [Convert]::ToBase64String(
        [Text.Encoding]::UTF8.GetBytes(($definition | ConvertTo-Json -Depth 20 -Compress))
    )
    $mirror = Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/mirroredDatabases" `
        -Headers $headers `
        -Body @{
            displayName = $MirrorName
            description = 'Oracle AI Database Free mirror for the Demo'
            definition = @{
                parts = @(
                    @{
                        path = 'mirroring.json'
                        payload = $payload
                        payloadType = 'InlineBase64'
                    }
                )
            }
        }
}

$status = $null
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $statusResponse = Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/mirroredDatabases/$($mirror.id)/getMirroringStatus" `
        -Headers $headers
    $status = $statusResponse.status
    if ($status -in 'Initialized', 'Stopped', 'Running') {
        break
    }
    if ($status -notin 'Initializing', 'Starting') {
        throw "Unexpected mirroring status: $status"
    }
    Start-Sleep -Seconds 10
}
if ($status -notin 'Initialized', 'Stopped', 'Running') {
    throw "Mirroring initialization timed out with status: $status"
}

if ($status -in 'Initialized', 'Stopped') {
    Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/mirroredDatabases/$($mirror.id)/startMirroring" `
        -Headers $headers | Out-Null
}

$tableNames = @(
    'DIM_DATE',
    'DIM_CUSTOMER',
    'DIM_PRODUCT',
    'DIM_STORE',
    'FACT_SALES'
)
$tablesStatus = $null
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    $tablesStatus = Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/mirroredDatabases/$($mirror.id)/getTablesMirroringStatus" `
        -Headers $headers
    $replicatingCount = @($tablesStatus.data | Where-Object status -eq 'Replicating').Count
    if ($replicatingCount -eq $tableNames.Count) {
        break
    }
    $failures = @($tablesStatus.data | Where-Object { $_.status -match 'Fail' })
    if ($failures.Count -gt 0) {
        throw "Mirroring failed for table $($failures[0].sourceTableName): $($failures[0].error.message)"
    }
    Start-Sleep -Seconds 10
}
if (@($tablesStatus.data | Where-Object status -eq 'Replicating').Count -ne $tableNames.Count) {
    throw 'The five Demo tables did not reach the Replicating state.'
}
$status = 'Running'

foreach ($tableName in $tableNames) {
    Invoke-FabricRequest `
        -Method Post `
        -Uri "$fabricBaseUri/workspaces/$($workspace.id)/items/$($lakehouse.id)/shortcuts?shortcutConflictPolicy=CreateOrOverwrite" `
        -Headers $headers `
        -Body @{
            path = 'Tables/DEMO_DW'
            name = $tableName
            target = @{
                oneLake = @{
                    workspaceId = $workspace.id
                    itemId = $mirror.id
                    path = "Tables/DEMO_DW/$tableName"
                }
            }
        } | Out-Null
}

$state.fabric = [pscustomobject]@{
    workspaceId = $workspace.id
    gatewayId = $gateway.id
    connectionId = $connection.id
    lakehouseId = $lakehouse.id
    mirrorId = $mirror.id
}
$state | ConvertTo-Json -Depth 12 | Set-Content -Path $StatePath -Encoding utf8NoBOM

Write-Output "FABRIC_CONNECTION=$($connection.displayName)"
Write-Output "FABRIC_LAKEHOUSE=$($lakehouse.displayName)"
Write-Output "FABRIC_MIRROR=$($mirror.displayName)"
Write-Output "MIRRORING_STATUS=$status"
Write-Output "SHORTCUT_COUNT=$($tableNames.Count)"
Write-Output 'DEPLOYMENT_USER_CONNECTION_ROLE=Owner'
