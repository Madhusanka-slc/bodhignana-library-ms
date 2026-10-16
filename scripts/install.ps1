<#
  Library system - one-step install and start on Windows.

  Run it by double-clicking install.bat (in the main folder), or from PowerShell:
      powershell -ExecutionPolicy Bypass -File scripts\install.ps1

  What it does, in order:
    1. Checks Docker Desktop is installed (offers to install it with winget if not)
    2. Starts Docker Desktop and waits until it is ready
    3. Creates the settings file (.env) with a random secret key and database password,
       and asks for the administrator password (an existing .env is kept as it is)
    4. Builds and starts the database, backend and frontend (docker compose)
    5. Waits until the system answers, then opens it in the browser
    6. Puts two shortcuts on the desktop: "Library System" and "Library Counter"
       (Library Counter prints receipts straight to the default printer, without the print window)

  Optional:
    -ImportFolder "D:\export"   import a J-ISIS export (userdb_flat.csv + libcat_flat.csv) after the start
    -RestoreFile  "D:\backup.sql"  load a backup made with backup.bat (replaces ALL data)
    -NoShortcuts                 do not create the desktop shortcuts
    -NoBrowser                   do not open the browser at the end

  It is safe to run again: it keeps the data and the .env, and only rebuilds and restarts.
#>
param(
  [string]$ImportFolder = "",
  [string]$RestoreFile = "",
  [switch]$NoShortcuts,
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Ok($text) { Write-Host "    $text" -ForegroundColor Green }
function Note($text) { Write-Host "    $text" -ForegroundColor Yellow }
function Fail($text) {
  Write-Host ""
  Write-Host "    $text" -ForegroundColor Red
  Write-Host ""
  Read-Host "Press Enter to close"
  exit 1
}

# Run docker and return $true when it worked (docker writes progress to stderr, which is not an error here)
function Docker-Ok {
  param([Parameter(ValueFromRemainingArguments = $true)] $DockerArgs)
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & docker @DockerArgs 2>&1 | Out-Null
  $code = $LASTEXITCODE
  $ErrorActionPreference = $old
  return ($code -eq 0)
}

function New-RandomText([int]$length) {
  $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'.ToCharArray()
  $bytes = New-Object byte[] $length
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

function Read-EnvValue($name, $default) {
  if (Test-Path .env) {
    $line = Get-Content .env | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -First 1
    if ($line) { return ($line -split '=', 2)[1].Trim() }
  }
  return $default
}

Write-Host ""
Write-Host "  Library system - install and start" -ForegroundColor White
Write-Host "  Folder: $root"

# ---------------------------------------------------------------- 1. Docker Desktop
Step "Checking Docker Desktop"
$dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  if (Test-Path $dockerDesktop) {
    # installed, but this window was opened before the install: add docker to PATH for now
    $env:Path += ";" + (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin')
  }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Note "Docker Desktop is not installed. It is needed to run the library system."
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/ , restart the PC, then run this again."
  }
  $answer = Read-Host "    Install Docker Desktop now? (Y/N)"
  if ($answer -notmatch '^[Yy]') { Fail "Install Docker Desktop, restart the PC, then run this again." }
  winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) { Fail "Docker Desktop could not be installed. Install it from https://www.docker.com/products/docker-desktop/ ." }
  Write-Host ""
  Note "Docker Desktop is installed. RESTART the PC, open Docker Desktop once (accept its terms),"
  Note "then run install.bat again to finish."
  Read-Host "Press Enter to close"
  exit 0
}
Ok "Docker is installed."

# ---------------------------------------------------------------- 2. Docker running
Step "Starting Docker"
if (-not (Docker-Ok info)) {
  if (Test-Path $dockerDesktop) {
    Start-Process $dockerDesktop
    Note "Docker Desktop is starting (this can take a minute or two)..."
  } else {
    Note "Please start Docker Desktop now."
  }
  $ready = $false
  foreach ($i in 1..90) {   # up to 3 minutes
    Start-Sleep -Seconds 2
    if (Docker-Ok info) { $ready = $true; break }
  }
  if (-not $ready) { Fail "Docker did not start. Open Docker Desktop, wait until it says 'Engine running', then run this again." }
}
Ok "Docker is running."
if (-not (Docker-Ok compose version)) { Fail "'docker compose' is missing. Update Docker Desktop, then run this again." }

# ---------------------------------------------------------------- 3. Settings file (.env)
Step "Settings file (.env)"
if (Test-Path .env) {
  Ok ".env already exists, it is kept as it is."
  if ((Read-EnvValue 'ADMIN_PASSWORD' '') -eq 'admin123') {
    Note "The administrator password in .env is still the default (admin123). Change it in the app: My account."
  }
} else {
  # A database made by an earlier install keeps its old password: only a brand-new database gets a random one.
  $project = (Split-Path -Leaf $root).ToLower() -replace '[^a-z0-9_-]', ''
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  $volumes = & docker volume ls -q 2>$null
  $ErrorActionPreference = $old
  $dbExists = @($volumes) -contains "${project}_pgdata"
  $dbPassword = if ($dbExists) { 'library' } else { New-RandomText 24 }
  if ($dbExists) { Note "Found the database of an earlier install: its data and password are kept." }

  Write-Host "    Choose the administrator password (user name: admin)."
  while ($true) {
    $p1 = Read-Host "    Password (at least 6 characters)" -AsSecureString
    $p2 = Read-Host "    Type it again" -AsSecureString
    $t1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p1))
    $t2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p2))
    if ($t1.Length -lt 6) { Note "Too short, try again."; continue }
    if ($t1 -ne $t2) { Note "The two passwords are different, try again."; continue }
    if ($t1 -match '[\s#"''=]') { Note "Please do not use spaces or the characters # "" ' = ."; continue }
    break
  }
  $port = Read-Host "    Web port (press Enter for 8080)"
  if (-not $port) { $port = '8080' }

  $envText = @(
    "# Made by install.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Keep this file private.",
    "DB_PASSWORD=$dbPassword",
    "SECRET_KEY=$(New-RandomText 48)",
    "ADMIN_USERNAME=admin",
    "ADMIN_PASSWORD=$t1",
    "APP_PORT=$port"
  ) -join "`r`n"
  [IO.File]::WriteAllText((Join-Path $root '.env'), $envText + "`r`n", (New-Object Text.UTF8Encoding $false))
  Ok ".env created (random secret key and database password)."
}
$port = Read-EnvValue 'APP_PORT' '8080'
$url = "http://localhost:$port"

# The web port must be free (or already used by this system)
$listener = Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  $owner = (Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue).ProcessName
  if ($owner -notmatch 'docker|wslrelay|com\.docker|vpnkit') {
    Fail "Port $port is used by another program ($owner). Change APP_PORT in .env, then run this again."
  }
}

# ---------------------------------------------------------------- 4. Build and start
Step "Building and starting the database, backend and frontend"
Note "The first time this downloads and builds everything: 5-15 minutes. Later runs are quick."
$old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
& docker compose up -d --build
$code = $LASTEXITCODE
$ErrorActionPreference = $old
if ($code -ne 0) { Fail "Starting failed (see the messages above). Check the internet connection and run this again." }
Ok "Containers are running."

# ---------------------------------------------------------------- 5. Wait until it answers
Step "Waiting for the library system to answer"
$up = $false
foreach ($i in 1..60) {   # up to 2 minutes
  try {
    $r = Invoke-WebRequest -Uri "$url/api/health" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $up = $true; break }
  } catch { }
  Start-Sleep -Seconds 2
}
if (-not $up) { Fail "The system did not answer on $url . See the logs with: docker compose logs backend" }
Ok "The system is running at $url"

# ---------------------------------------------------------------- Optional: restore a backup / import J-ISIS data
if ($RestoreFile) {
  Step "Restoring the backup $RestoreFile"
  if (-not (Test-Path $RestoreFile)) { Fail "Backup file not found: $RestoreFile" }
  $answer = Read-Host "    This REPLACES ALL current data with the backup. Type YES to continue"
  if ($answer -ceq 'YES') {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    # copied into the container (not piped) so Sinhala and other non-English text stays intact
    & docker compose cp $RestoreFile db:/tmp/restore.sql | Out-Null
    & docker compose exec -T db psql -U library -d library -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" | Out-Null
    & docker compose exec -T db psql -U library -d library -q -f /tmp/restore.sql | Out-Null
    & docker compose exec -T db rm -f /tmp/restore.sql | Out-Null
    & docker compose restart backend | Out-Null
    $ErrorActionPreference = $old
    Ok "Backup restored."
  } else { Note "Restore skipped." }
}

if ($ImportFolder) {
  Step "Importing the J-ISIS export from $ImportFolder"
  foreach ($f in 'userdb_flat.csv', 'libcat_flat.csv') {
    if (-not (Test-Path (Join-Path $ImportFolder $f))) { Fail "$f not found in $ImportFolder" }
  }
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  & docker compose exec -T backend mkdir -p /tmp/export | Out-Null
  & docker compose cp (Join-Path $ImportFolder 'userdb_flat.csv') backend:/tmp/export/userdb_flat.csv | Out-Null
  & docker compose cp (Join-Path $ImportFolder 'libcat_flat.csv') backend:/tmp/export/libcat_flat.csv | Out-Null
  & docker compose cp scripts/import_jisis.py backend:/tmp/import_jisis.py | Out-Null
  Note "Test run first (nothing is saved):"
  & docker compose exec -T backend python /tmp/import_jisis.py /tmp/export --dry-run
  $ErrorActionPreference = $old
  $answer = Read-Host "    Import for real now? (Y/N)"
  if ($answer -match '^[Yy]') {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & docker compose exec -T backend python /tmp/import_jisis.py /tmp/export
    $ErrorActionPreference = $old
    Ok "Import finished."
  } else { Note "Import skipped." }
}

# ---------------------------------------------------------------- 6. Desktop shortcuts
if (-not $NoShortcuts) {
  Step "Creating desktop shortcuts"
  $desktop = [Environment]::GetFolderPath('Desktop')
  $shell = New-Object -ComObject WScript.Shell
  $edge = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe')
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1

  # Library System: the normal browser
  $web = $shell.CreateShortcut((Join-Path $desktop 'Library System.lnk'))
  $web.TargetPath = $url
  $web.Save()

  # Library Counter: its own Edge window that prints straight to the default printer (no print dialog)
  if ($edge) {
    $profileDir = Join-Path $env:LOCALAPPDATA 'LibraryCounter'
    $counter = $shell.CreateShortcut((Join-Path $desktop 'Library Counter.lnk'))
    $counter.TargetPath = $edge
    $counter.Arguments = "--app=$url --kiosk-printing --user-data-dir=`"$profileDir`" --start-maximized"
    $counter.IconLocation = "$edge,0"
    $counter.Description = 'Library counter: prints receipts directly to the default printer'
    $counter.Save()
    Ok "'Library System' and 'Library Counter' are on the desktop."
  } else {
    Ok "'Library System' is on the desktop (Edge not found, so no 'Library Counter' shortcut)."
  }
}

# ---------------------------------------------------------------- Done
Write-Host ""
Write-Host "  Done. The library system is running at $url" -ForegroundColor Green
Write-Host "  Sign in as 'admin' with the administrator password from .env."
Write-Host "  Other PCs in the library: http://<this PC's IP address>:$port"
Write-Host "  It starts by itself with Docker Desktop (turn on 'Start Docker Desktop when you sign in')."
Write-Host "  Back up every day with scripts\backup.bat."
Write-Host ""
if (-not $NoBrowser) { Start-Process $url }
Read-Host "Press Enter to close"
