[CmdletBinding(DefaultParameterSetName = 'Peer')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Peer')]
    [switch] $Peer,

    [Parameter(Mandatory, ParameterSetName = 'Full')]
    [string] $PeerEvidence,

    [Parameter(Mandatory)]
    [string] $OutputFile
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env'

function Invoke-Docker {
    param([string[]] $Arguments)

    $lines = @(& docker @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') exited with code $LASTEXITCODE"
    }
    return ($lines -join [Environment]::NewLine)
}

function Confirm-Check {
    param([bool] $Condition, [string] $Message)

    if (-not $Condition) { throw $Message }
}

$context = (Invoke-Docker @('context', 'show')).Trim()
$endpoint = if ($env:DOCKER_HOST -and -not $env:DOCKER_CONTEXT) {
    $env:DOCKER_HOST
} else {
    (Invoke-Docker @('context', 'inspect', $context, '--format', '{{.Endpoints.docker.Host}}')).Trim()
}
Confirm-Check ($endpoint -match '^(npipe|unix):') 'Select the Docker engine on this computer before capturing evidence.'

if ($Peer) {
    $node = 'B'
    $shard = 'shard2'
    $port = 27021
    $composeFile = 'compose.peer.yaml'
    $remoteHosts = @('gowalla-cfg', 'gowalla-shard1')
} else {
    $node = 'A'
    $shard = 'shard1'
    $port = 27011
    $composeFile = 'compose.yaml'
    $remoteHosts = @('gowalla-shard2')
}

$compose = @('compose', '--project-directory', $root, '--env-file', $envFile, '-f', (Join-Path $root $composeFile))
$containerId = (Invoke-Docker ($compose + @('ps', '-q', $shard))).Trim()
Confirm-Check ($containerId -match '^[0-9a-f]{12,64}$') "$shard must be running on this computer."
$container = Invoke-Docker @('inspect', '--format', '{{json .}}', $containerId) | ConvertFrom-Json
$bindings = @($container.NetworkSettings.Ports."$port/tcp")
Confirm-Check ($bindings.Count -eq 1 -and $bindings[0].HostPort -eq "$port") "Expected one LAN port binding for $shard."
$addresses = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
    ForEach-Object { $_.GetIPProperties().UnicastAddresses } |
    Where-Object { $_.Address.AddressFamily -eq 'InterNetwork' -and -not [System.Net.IPAddress]::IsLoopback($_.Address) } |
    ForEach-Object { $_.Address.IPAddressToString }
$localAddress = $bindings[0].HostIp
Confirm-Check ($localAddress -in $addresses) "Published address $localAddress is not a LAN address on this computer."

$peerAddresses = foreach ($alias in $remoteHosts) {
    $aliasPrefix = '^' + [regex]::Escape($alias) + '[:=]'
    $entry = @($container.HostConfig.ExtraHosts | Where-Object { $_ -match $aliasPrefix })
    Confirm-Check ($entry.Count -eq 1) "Missing address mapping for $alias."
    $entry[0] -replace $aliasPrefix, ''
}
$peerAddresses = @($peerAddresses | Select-Object -Unique)
Confirm-Check ($peerAddresses.Count -eq 1 -and $peerAddresses[0] -ne $localAddress) 'The configured peer must have a distinct LAN address.'

$mount = @($container.Mounts | Where-Object { $_.Destination -eq '/data/db' })
Confirm-Check ($mount.Count -eq 1 -and $mount[0].Type -eq 'volume' -and $mount[0].RW) 'The shard data path must be backed by one writable Docker volume.'
$volume = Invoke-Docker @('volume', 'inspect', '--format', '{{json .}}', $mount[0].Name) | ConvertFrom-Json
Confirm-Check ($volume.Driver -eq 'local' -and $null -eq $volume.Options) 'Expected a local data volume without remote mount options.'

$daemonId = (Invoke-Docker @('info', '--format', '{{.ID}}')).Trim()
Confirm-Check (-not [string]::IsNullOrWhiteSpace($daemonId)) 'Docker did not return an engine ID.'
if (-not $Peer) {
    $remote = Get-Content -Raw -Encoding UTF8 -LiteralPath $PeerEvidence | ConvertFrom-Json
    Confirm-Check (
        $remote.node -eq 'B' -and $remote.database.replica_set -eq 'shard2' -and
        $remote.database.namespace -eq 'gowalla.checkins' -and $remote.database.documents -gt 0 -and
        -not [string]::IsNullOrWhiteSpace($remote.docker_engine_id) -and
        $remote.docker_engine_id -ne $daemonId -and
        -not [string]::IsNullOrWhiteSpace($remote.computer_name) -and
        $remote.container_id -match '^[0-9a-f]{64}$' -and $remote.container_id -ne $container.Id -and
        $remote.published_port -eq 27021 -and -not [string]::IsNullOrWhiteSpace($remote.data_volume) -and
        $remote.published_ipv4 -eq $peerAddresses[0] -and $remote.peer_ipv4 -eq $localAddress
    ) 'Peer evidence must identify shard2 on the configured B address and a separate Docker engine.'
}

$localUri = 'mongodb://127.0.0.1:' + $port + '/?directConnection=true'
$local = Invoke-Docker ($compose + @('exec', '-T', $shard, 'mongosh', $localUri, '--quiet', '--file', '/scripts/verify_local_shard.js')) | ConvertFrom-Json
Confirm-Check ($local.replica_set -eq $shard -and $local.advertised_member -eq "gowalla-$($shard):$port") "Unexpected replica identity for $shard."
$evidence = [ordered]@{
    node = $node
    computer_name = [Environment]::MachineName
    collected_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    docker_context = $context
    docker_engine_id = $daemonId
    published_ipv4 = $localAddress
    peer_ipv4 = $peerAddresses[0]
    published_port = $port
    container_id = $container.Id
    data_volume = $mount[0].Name
    database = $local
}

if (-not $Peer) {
    $remoteUri = 'mongodb://gowalla-shard2:27021/?directConnection=true'
    $remoteRead = Invoke-Docker ($compose + @('exec', '-T', 'mongos', 'mongosh', $remoteUri, '--quiet', '--file', '/scripts/verify_local_shard.js')) | ConvertFrom-Json
    Confirm-Check (
        $remoteRead.replica_set -eq 'shard2' -and $remoteRead.advertised_member -eq 'gowalla-shard2:27021' -and
        $remote.database.advertised_member -eq $remoteRead.advertised_member -and
        $remoteRead.documents -eq $remote.database.documents -and
        $remoteRead.sample.source_line -eq $remote.database.sample.source_line -and
        $remoteRead.sample.user_id -eq $remote.database.sample.user_id -and
        $remoteRead.sample.timestamp.'$date' -eq $remote.database.sample.timestamp.'$date' -and
        $local.sample.source_line -ne $remoteRead.sample.source_line
    ) 'The direct read from A does not match the independent evidence from B.'

    $cluster = Invoke-Docker ($compose + @('exec', '-T', 'mongos', 'mongosh', '--quiet', '--file', '/scripts/verify_distribution.js')) | ConvertFrom-Json
    $shards = @($cluster.distribution[0].shards | Sort-Object shardName)
    $registered = @($cluster.shard_hosts | Sort-Object name)
    Confirm-Check (
        $registered.Count -eq 2 -and $registered[0].connection -eq "shard1/$($local.advertised_member)" -and
        $registered[1].connection -eq "shard2/$($remoteRead.advertised_member)" -and
        $shards.Count -eq 2 -and $shards[0].shardName -eq 'shard1' -and $shards[1].shardName -eq 'shard2' -and
        $shards[0].numOrphanedDocs -eq 0 -and $shards[1].numOrphanedDocs -eq 0
    ) 'The configured shards and owned-data statistics did not match the two physical hosts.'
    Confirm-Check (
        $cluster.input_count -eq 6442892 -and $cluster.reject_count -eq 765 -and $cluster.clean_count -eq 6442127 -and
        $cluster.total_count -eq $cluster.clean_count -and
        $shards[0].numOwnedDocuments -eq $local.documents -and
        $shards[1].numOwnedDocuments -eq $remoteRead.documents -and
        ($local.documents + $remoteRead.documents) -eq $cluster.total_count
    ) 'Full-data counts do not reconcile across the local shards and mongos.'
    Confirm-Check (
        @($cluster.trajectory_shards).Count -eq 1 -and
        $cluster.trajectory_shards[0] -in @('shard1', 'shard2') -and
        $cluster.trajectory_user_0_count -eq 225 -and
        ($cluster.region_shards -join ',') -eq 'shard1,shard2' -and
        $cluster.region_source_line_1_found
    ) 'Trajectory or spatial routing did not match the acceptance criteria.'

    $evidence = [ordered]@{
        status = 'passed'
        host_a = $evidence
        host_b = $remote
        host_a_direct_read_of_shard2 = $remoteRead
        cluster = $cluster
    }
}

$target = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputFile)
[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
[IO.File]::WriteAllText($target, ($evidence | ConvertTo-Json -Depth 70) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Output "Evidence written to $target"
