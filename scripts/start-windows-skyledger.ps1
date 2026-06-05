param(
    [string]$Config = "",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Missing virtualenv Python at $Python. Create .venv and install requirements first."
}

if (-not $Config) {
    if (Test-Path (Join-Path $ProjectRoot "config.windows.local.yaml")) {
        $Config = "config.windows.local.yaml"
    }
    else {
        $Config = "config.windows.yaml"
    }
}

& $Python -m skyledger --config $Config --host $HostName --port $Port
