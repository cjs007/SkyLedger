param(
    [string]$InstallPath = "$env:LOCALAPPDATA\SkyLedger\Dump1090",
    [int]$HttpPort = 8080,
    [double]$Gain = 31,
    [bool]$ErrorCorrect1 = $true,
    [bool]$ErrorCorrect2 = $false
)

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/gvanem/Dump1090.git"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$CandidateConfigPaths = @(
    (Join-Path $ProjectRoot "config.windows.local.yaml"),
    (Join-Path $ProjectRoot "config.local.yaml"),
    (Join-Path $ProjectRoot "config.windows.yaml"),
    (Join-Path $ProjectRoot "config.yaml")
)
$AppConfigPath = $CandidateConfigPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

function Get-SimpleYamlValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $match = Select-String -Path $Path -Pattern "^\s*$([regex]::Escape($Key))\s*:\s*(.+?)\s*$" | Select-Object -First 1
    if (-not $match) {
        return $null
    }

    return $match.Matches[0].Groups[1].Value.Trim(" `"'")
}

$HomeLat = Get-SimpleYamlValue -Path $AppConfigPath -Key "home_lat"
$HomeLon = Get-SimpleYamlValue -Path $AppConfigPath -Key "home_lon"
if (-not $HomeLat -or -not $HomeLon) {
    throw "Could not read home_lat/home_lon from $AppConfigPath"
}

if (-not (Test-Path (Join-Path $InstallPath "dump1090.exe"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $InstallPath) | Out-Null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git clone --depth 1 $RepoUrl $InstallPath
    }
    else {
        $zipPath = Join-Path $env:TEMP "Dump1090-main.zip"
        $extractPath = Join-Path $env:TEMP "Dump1090-main"
        Remove-Item -LiteralPath $zipPath,$extractPath -Recurse -Force -ErrorAction SilentlyContinue
        Invoke-WebRequest -Uri "https://github.com/gvanem/Dump1090/archive/refs/heads/main.zip" -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $extractPath
        Move-Item -Path (Join-Path $extractPath "Dump1090-main") -Destination $InstallPath
    }
}

$BaseConfig = Join-Path $InstallPath "dump1090.cfg"
$LocalConfig = Join-Path $InstallPath "skyledger-windows.cfg"
if (-not (Test-Path $BaseConfig)) {
    throw "Missing Dump1090 config: $BaseConfig"
}

$Content = Get-Content -Path $BaseConfig -Raw
$Content = $Content -replace "(?m)^homepos\s*=.*$", "homepos          = $HomeLat,$HomeLon"
$Content = $Content -replace "(?m)^net-http-port\s*=.*$", "net-http-port   = $HttpPort"
$Content = $Content -replace "(?m)^gain\s*=.*$", "gain       = $Gain"
$Content = $Content -replace "(?m)^error-correct1\s*=.*$", "error-correct1   = $($ErrorCorrect1.ToString().ToLower())"
$Content = $Content -replace "(?m)^error-correct2\s*=.*$", "error-correct2   = $($ErrorCorrect2.ToString().ToLower())"
$Content = $Content -replace "(?m)^logfile\s*=.*$", "logfile          = NUL"
$Content = $Content -replace "(?m)^http-log\s*=.*$", "# http-log        = false"
$Content = $Content -replace "(?m)^http-log-name\s*=.*$", "# http-log-name   = %TEMP%\dump1090\http.log"
Set-Content -Path $LocalConfig -Value $Content -Encoding ASCII

Write-Host "Starting Dump1090 for SkyLedger Windows development"
Write-Host "Install path: $InstallPath"
Write-Host "Home position: loaded from $(Split-Path $AppConfigPath -Leaf)"
Write-Host "Gain: $Gain dB"
Write-Host "Error correction: 1-bit=$ErrorCorrect1, 2-bit=$ErrorCorrect2"
Write-Host "Aircraft JSON: http://127.0.0.1:$HttpPort/data/aircraft.json"
Write-Host "Map/UI: http://127.0.0.1:$HttpPort/"
Write-Host ""
Write-Host "Leave this window open while SkyLedger is running."

& (Join-Path $InstallPath "dump1090.exe") --config $LocalConfig --net
