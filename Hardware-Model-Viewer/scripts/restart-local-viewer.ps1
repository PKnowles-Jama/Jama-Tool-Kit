$ErrorActionPreference = 'Stop'
$viewerRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$viewerPython = Join-Path $viewerRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $viewerPython)) { throw 'Viewer virtual environment is missing.' }
$viewerConfigPath = Join-Path $viewerRoot 'config\local.json'
$viewerConfig = Get-Content -LiteralPath $viewerConfigPath -Raw | ConvertFrom-Json
if ($viewerConfig.publicOrigin -ne 'https://localhost:8444') { throw 'This helper is scoped to the local port-8444 viewer.' }
$viewerListeners = @(Get-NetTCPConnection -State Listen -LocalPort 8090 -ErrorAction SilentlyContinue)
foreach ($viewerPid in ($viewerListeners.OwningProcess | Select-Object -Unique)) {
    $viewerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $viewerPid"
    if ($viewerProcess.CommandLine -notlike "*$viewerRoot*" -or $viewerProcess.CommandLine -notmatch 'viewer\.py\s+serve') {
        throw 'Port 8090 belongs to an unrecognized process; it was not stopped.'
    }
    Stop-Process -Id $viewerPid
}
$viewerLogs = Join-Path $viewerRoot 'logs'
New-Item -ItemType Directory -Path $viewerLogs -Force | Out-Null
$viewerStarted = Start-Process -FilePath $viewerPython -ArgumentList @('viewer.py', 'serve', '--config', 'config/local.json') -WorkingDirectory $viewerRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $viewerLogs 'local-viewer.out.log') -RedirectStandardError (Join-Path $viewerLogs 'local-viewer.err.log')
for ($viewerAttempt = 0; $viewerAttempt -lt 15; $viewerAttempt++) {
    try {
        $viewerHealth = Invoke-WebRequest -Uri 'http://127.0.0.1:8090/health' -UseBasicParsing -TimeoutSec 2
        if ($viewerHealth.StatusCode -eq 200) {
            Write-Output 'Local viewer restarted and healthy. Existing Caddy process was left running.'
            exit 0
        }
    } catch { Start-Sleep -Milliseconds 250 }
}
throw 'Viewer did not become healthy; inspect logs/local-viewer.err.log.'
