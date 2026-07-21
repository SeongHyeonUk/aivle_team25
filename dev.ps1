[CmdletBinding()]
param(
    [switch]$SkipDatabase
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend"
$gradleWrapper = Join-Path $projectRoot "gradlew.bat"

if (-not (Test-Path -LiteralPath $gradleWrapper)) {
    throw "gradlew.bat was not found: $gradleWrapper"
}

if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
    throw "Java was not found. Install Java 17 or newer and add it to PATH."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js/npm and add them to PATH."
}

if (-not $SkipDatabase) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "[1/3] Starting the MySQL container..." -ForegroundColor Cyan
        & docker compose --project-directory $projectRoot up -d mysql
        if ($LASTEXITCODE -ne 0) {
            throw "Could not start MySQL. Check that Docker Desktop is running."
        }
    }
    else {
        Write-Warning "Docker was not found, so MySQL startup was skipped. MySQL must already be available at localhost:3307."
    }
}
else {
    Write-Host "[1/3] Skipping MySQL startup." -ForegroundColor DarkGray
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules"))) {
    Write-Host "[2/3] Installing frontend packages..." -ForegroundColor Cyan
    Push-Location $frontendRoot
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed."
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "[2/3] Frontend packages are already installed." -ForegroundColor DarkGray
}

$backendCommand = "Set-Location -LiteralPath '$($projectRoot.Replace("'", "''"))'; & '.\gradlew.bat' ':backend:bootRun'"
$frontendCommand = "Set-Location -LiteralPath '$($frontendRoot.Replace("'", "''"))'; npm run dev"

Write-Host "[3/3] Starting backend and frontend in separate windows..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand)
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand)

Write-Host ""
Write-Host "Startup complete." -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:8080"
Write-Host "Press Ctrl+C in each new window to stop its server."
