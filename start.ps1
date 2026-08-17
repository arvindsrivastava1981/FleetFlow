# ============================================================================
#  start.ps1  -  FleetFlow launcher: validate install, then start the app
# ============================================================================
#  Cross-references:  Installation.md  (sections 1-6)
#
#  Two-phase operation:
#    1) Validates the install (prereqs, deps, env, schema, entry points) —
#       a non-mutating status snapshot (Installation.md sections 1-6).
#       Optional items (.venv, incremental.sql) are reported but not fatal.
#    2) If all required checks PASS, starts the PRIMARY / DEPLOY entry point
#       (Installation.md section 5):
#           uvicorn backend.app.main:app --host 0.0.0.0 --port <PORT>
#       Default port is 10000; override with -Port <n> or $env:PORT.
#
# Flags:
#    -CheckOnly       Run only the validation phase (no server start).
#    -Port <int>      Port to bind (default 10000; falls back to $env:PORT).
#
# Examples:
#    powershell -File start.ps1 -CheckOnly       # just the status snapshot
#    powershell -File start.ps1                  # validate, then start app on :10000
#    powershell -File start.ps1 -Port 9000       # validate, then start app on :9000
# ============================================================================

param(
    [switch]$CheckOnly,
    [int]$Port = 10000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Resolve bind port: explicit -Port wins; else $env:PORT; else 10000 ------
if (-not $PSBoundParameters.ContainsKey('Port') -and $env:PORT) {
    $BoundPort = [int]$env:PORT
}
else {
    $BoundPort = $Port
}

# --- Repo root = directory containing this script ---------------------------
$Root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvRef = Join-Path $Root 'Installation.md'

# Manage checks: keep a counter so *all* checks run, then fail once at the end.
# Use the same $global:Fail scope everywhere so the summary read never hits an
# undefined variable (matches the variable set by Write-Check on a FAIL).
$global:Fail = 0

function Write-Check {
    param(
        [string]$Label,
        [bool]$Pass,
        [string]$Detail = '',
        [switch]$Optional
    )
    $mark = if ($Pass) { 'PASS' } else { 'FAIL' }
    if (-not $Pass -and -not $Optional) { $global:Fail = 1 }
    $line = "[{0}] {1}" -f $mark, $Label
    if ($Detail) { $line += " - $Detail" }
    Write-Host $line
}

Write-Host ''
Write-Host 'FleetFlow installation status  (reference: Installation.md)'
Write-Host ('Root: ' + $Root)
Write-Host ('-' * 60)

# --- [0] Reference doc present ----------------------------------------------
Write-Check -Label 'Installation.md exists in repo root' -Pass (Test-Path $EnvRef)
# --- [1] Prerequisites: Python 3.12+ ---------------------------------------
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVerRaw = (python --version) 2>&1
    $pyMatch  = [regex]::Match($pyVerRaw, 'Python (\d+)\.(\d+)\.?(\d*)')
    if ($pyMatch.Success) {
        $mm = [int]$pyMatch.Groups[1].Value * 100 + [int]$pyMatch.Groups[2].Value
        $verString = $pyMatch.Groups[1].Value + '.' + $pyMatch.Groups[2].Value
        Write-Check -Label "Python 3.12+ (found $verString)" -Pass ($mm -ge 312) -Detail 'Installation.md section 1'
    }
    else {
        Write-Check -Label 'Python version unreadable' -Pass $false
    }
}
else {
    Write-Check -Label 'Python not found on PATH' -Pass $false -Detail 'Installation.md section 1'
}

# Virtual environment (recommended, not mandatory)
$venvPy = Join-Path (Join-Path $Root '.venv') (Join-Path 'Scripts' 'python.exe')
Write-Check -Label 'Virtual environment (.venv) present' -Pass (Test-Path $venvPy) -Detail 'optional, Installation.md section 1' -Optional

# --- [2] Dependencies -------------------------------------------------------
$reqFile = Join-Path $Root 'requirements.txt'
if (Test-Path $reqFile) {
    $req = Get-Content $reqFile | Where-Object { $_ -match '^\S' -and $_ -notmatch '^\s*#' }
    $installed = (pip list --format=freeze 2>&1) -join "`n"
    $missing = @()
    foreach ($r in $req) {
        # Normalize requirement name: strip version spec and extra markers
        # (e.g. "uvicorn[standard]" -> "uvicorn") so it matches pip freeze names.
        $name = (($r -split '[><=]')[0] -replace '\[.*\]', '').Trim()
        if ($name -and $installed -notmatch [regex]::Escape($name)) { $missing += $name }
    }
    $depDetail = if ($missing.Count -gt 0) { ("missing: " + ($missing -join ', ')) } else { 'all requirements found' }
    Write-Check -Label 'Dependencies installed (pip)' -Pass ($missing.Count -eq 0) -Detail $depDetail
}
else {
    Write-Check -Label 'requirements.txt exists' -Pass $false -Detail 'Installation.md section 2'
}
# --- [3] Environment configuration -----------------------------------------
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
    $envLines = Get-Content $envFile | Where-Object { $_ -match '=' -and $_ -notmatch '^\s*#' }
    $hasDb  = [bool]($envLines | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' -and $_ -notmatch '=\s*$' })
    $hasPw  = [bool]($envLines | Where-Object { $_ -match '^\s*ADMIN_PASSWORD\s*=' -and $_ -notmatch '=\s*$' })
    Write-Check -Label 'DATABASE_URL set in .env'     -Pass $hasDb -Detail 'required always, Installation.md section 3'
    Write-Check -Label 'ADMIN_PASSWORD set in .env'   -Pass $hasPw -Detail 'required in production, Installation.md section 3'
}
else {
    Write-Check -Label '.env file exists' -Pass $false -Detail 'Installation.md section 3'
}

# --- [4] Database schema (never applied by the app) -------------------------
Write-Check -Label 'database/schema.sql exists'       -Pass (Test-Path (Join-Path (Join-Path $Root 'database') 'schema.sql')) -Detail 'Installation.md section 4'
Write-Check -Label 'database/incremental.sql exists'  -Pass (Test-Path (Join-Path (Join-Path $Root 'database') 'incremental.sql')) -Detail 'optional (older schema), Installation.md section 4' -Optional

# --- [5] Entry points -------------------------------------------------------
Write-Check -Label 'backend/app/main.py (modular deploy target)' -Pass (Test-Path (Join-Path (Join-Path (Join-Path $Root 'backend') 'app') 'main.py')) -Detail 'Installation.md section 5'
Write-Check -Label 'fleetflow_interactive_demo.py (legacy dev tool)' -Pass (Test-Path (Join-Path $Root 'fleetflow_interactive_demo.py')) -Detail 'Installation.md section 5'
Write-Check -Label 'utils.py at repo root (legacy dep)' -Pass (Test-Path (Join-Path $Root 'utils.py')) -Detail 'Installation.md section 5'

# --- [6] Validation scripts -------------------------------------------------
Write-Check -Label 'scripts/smoke_check.py exists' -Pass (Test-Path (Join-Path (Join-Path $Root 'scripts') 'smoke_check.py')) -Detail 'Installation.md section 6'
Write-Check -Label 'scripts/run_tests.py exists'    -Pass (Test-Path (Join-Path (Join-Path $Root 'scripts') 'run_tests.py')) -Detail 'Installation.md section 6'
# --- Summary & start ---------------------------------------------------------
Write-Host ('-' * 60)

if ($global:Fail -ne 0) {
    Write-Host 'STAT: CHECKS FAILED - review the FAIL lines; see Installation.md for steps.' -ForegroundColor Red
    Write-Host '       Install deps  : pip install -r requirements.txt      (section 2)'
    Write-Host '       Configure env : create .env (see Installation.md)    (section 3)'
    Write-Host '       Apply schema   : psql "$DATABASE_URL" -f database/schema.sql (section 4)'
    Write-Host '       Run app        : uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000} (section 5)'
    Write-Host ''
    exit $global:Fail
}

Write-Host 'STAT: OK - install matches Installation.md (file-presence + env snapshot).' -ForegroundColor Green
Write-Host ''

if ($CheckOnly) {
    Write-Host 'CheckOnly mode: validation passed; not starting the server.' -ForegroundColor Cyan
    Write-Host ''
    exit 0
}

# All required checks passed -> start the PRIMARY / DEPLOY entry point.
$modApp = Join-Path (Join-Path (Join-Path $Root 'backend') 'app') 'main.py'
if (-not (Test-Path $modApp)) {
    Write-Host "ERROR: $modApp not found; cannot start." -ForegroundColor Red
    exit 1
}

Set-Location $Root
Write-Host ('Starting FleetFlow on http://0.0.0.0:{0}  (primary/deploy entry point, Installation.md section 5)' -f $BoundPort) -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop.' -ForegroundColor DarkGray
Write-Host ''

# python -m uvicorn is more robust than the bare `uvicorn` shim (venv-friendly)
# and resolves the backend package + .env from the repo root (Set-Location above).
& python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $BoundPort
exit $LASTEXITCODE