param(
    [string]$HostName = "server-shu",
    [string]$RemoteRawDir = "/opt/ultrafast_laser_process_decision_agent/.runtime-state/data/raw"
)

$ErrorActionPreference = "Stop"
$files = @("AlSiC.csv", "CFRP.csv", "SiC.csv", "ZrO2.csv")
$root = Split-Path -Parent $PSScriptRoot

foreach ($name in $files) {
    $local = Join-Path $root "data/raw/$name"
    if (-not (Test-Path -LiteralPath $local -PathType Leaf)) {
        throw "Missing local raw CSV: $local"
    }
    $hash = (Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash.ToLowerInvariant()
    $remote = "$RemoteRawDir/$name"
    $remoteHash = ssh -o BatchMode=yes $HostName "if test -f '$remote'; then sha256sum '$remote' | cut -d ' ' -f1; fi"
    if ($remoteHash) {
        if ($remoteHash.Trim().ToLowerInvariant() -ne $hash) {
            throw "Remote raw CSV differs and will not be overwritten: $remote"
        }
        Write-Output "Verified existing $name ($hash)"
        continue
    }
    $temporary = "$remote.uploading-$hash"
    scp -- $local "${HostName}:$temporary"
    $uploadedHash = ssh -o BatchMode=yes $HostName "sha256sum '$temporary' | cut -d ' ' -f1"
    if ($uploadedHash.Trim().ToLowerInvariant() -ne $hash) {
        ssh -o BatchMode=yes $HostName "rm -f '$temporary'"
        throw "Remote checksum mismatch for $name"
    }
    ssh -o BatchMode=yes $HostName "mv -n '$temporary' '$remote'"
    Write-Output "Uploaded $name ($hash)"
}
