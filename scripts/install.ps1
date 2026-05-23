# Discord Helper — Windows Installer
# Usage: iwr -useb https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.ps1 | iex
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$AppName   = "discord-helper"
$RepoUrl   = "https://github.com/JoseISC/Discord-Helper.git"
$Branch    = if ($env:DISCORD_HELPER_BRANCH) { $env:DISCORD_HELPER_BRANCH } else { "instalador" }
$InstallDir = "$env:LOCALAPPDATA\$AppName\source"

function Write-Step  { Write-Host "`n$args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "  [OK]  $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "  [!]   $args" -ForegroundColor Yellow }
function Write-Fail  { Write-Host "`n[ERROR] $args" -ForegroundColor Red; exit 1 }

# ── Python ────────────────────────────────────────────────────────────────────

function Ensure-Python {
    Write-Step "Checking Python..."
    try {
        $ver = python --version 2>&1
        $parts = ($ver -replace "Python ","").Split(".")
        if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
            Write-Fail "Python 3.10+ required. Found: $ver`nInstall via: winget install Python.Python.3.12"
        }
        Write-OK "Python: $ver"
    } catch {
        Write-Warn "Python not found."
        Write-Warn "Installing Python 3.12 via winget..."
        try {
            winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
            Write-OK "Python installed. Please reopen this terminal and rerun the installer."
            exit 0
        } catch {
            Write-Fail "Could not install Python automatically.`nVisit: https://www.python.org/downloads/"
        }
    }
}

# ── git ───────────────────────────────────────────────────────────────────────

function Ensure-Git {
    Write-Step "Checking git..."
    try {
        $v = git --version 2>&1
        Write-OK "git: $v"
    } catch {
        Write-Warn "git not found. Installing via winget..."
        try {
            winget install --id Git.Git --silent --accept-package-agreements --accept-source-agreements
            Write-OK "git installed. Please reopen this terminal and rerun the installer."
            exit 0
        } catch {
            Write-Fail "Could not install git automatically.`nVisit: https://git-scm.com/downloads"
        }
    }
}

# ── pipx ─────────────────────────────────────────────────────────────────────

function Ensure-Pipx {
    Write-Step "Checking pipx..."
    try {
        $v = pipx --version 2>&1
        Write-OK "pipx: $v"
    } catch {
        Write-Warn "pipx not found — installing..."
        python -m pip install --user --quiet pipx
        python -m pipx ensurepath | Out-Null
        Write-OK "pipx installed"
    }
}

# ── FFmpeg ────────────────────────────────────────────────────────────────────

function Install-FFmpeg {
    Write-Step "Checking FFmpeg..."
    try {
        $v = ffmpeg -version 2>&1 | Select-Object -First 1
        Write-OK "FFmpeg: $v"
    } catch {
        Write-Warn "FFmpeg not found — downloading..."
        $ffmpegScript = Join-Path $PSScriptRoot "windows\install_ffmpeg.ps1"
        if (Test-Path $ffmpegScript) {
            & $ffmpegScript
        } else {
            # Run inline if script not on disk (piped install scenario)
            $target = "$HOME\.local\bin\$AppName\ffmpeg"
            $tempZip = "$env:TEMP\ffmpeg-release.zip"
            New-Item -ItemType Directory -Force -Path $target | Out-Null
            $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            Write-Host "  Downloading FFmpeg from $url ..."
            Invoke-WebRequest -Uri $url -OutFile $tempZip -UseBasicParsing
            Expand-Archive -Force $tempZip $target

            # Find the bin folder and add to user PATH
            $binDir = (Get-ChildItem -Path $target -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1).DirectoryName
            if ($binDir) {
                $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
                if ($currentPath -notlike "*$binDir*") {
                    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$binDir", "User")
                }
                Write-OK "FFmpeg installed at: $binDir"
            }
        }
    }
}

# ── source clone ──────────────────────────────────────────────────────────────

function Install-Source {
    Write-Step "Setting up source at $InstallDir..."
    if (Test-Path (Join-Path $InstallDir ".git")) {
        git -C $InstallDir fetch --quiet origin $Branch
        git -C $InstallDir checkout --quiet $Branch
        git -C $InstallDir pull --quiet origin $Branch
        Write-OK "Source updated"
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $InstallDir) | Out-Null
        git clone --quiet --branch $Branch $RepoUrl $InstallDir
        Write-OK "Source cloned"
    }
}

# ── pipx install ──────────────────────────────────────────────────────────────

function Install-Package {
    Write-Step "Installing discord-helper via pipx..."
    pipx install --force "$InstallDir[windows]"
    Write-OK "discord-helper installed"
}

# ── verify ────────────────────────────────────────────────────────────────────

function Verify-Install {
    try {
        $bin = (Get-Command discord-helper -ErrorAction Stop).Source
        Write-OK "Binary: $bin"
    } catch {
        Write-Warn "discord-helper not in PATH yet."
        Write-Warn "Run: `$env:PATH += `";`$env:USERPROFILE\.local\bin`""
        Write-Warn "Or restart your terminal."
    }
}

# ── main ──────────────────────────────────────────────────────────────────────

Write-Host "`nDiscord Helper — Windows Installer" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

Ensure-Python
Ensure-Git
Ensure-Pipx
Install-Source
Install-Package
Install-FFmpeg
Verify-Install

Write-Host "`nInstallation complete!" -ForegroundColor Green
Write-Host "`nNext steps:"
Write-Host "  discord-helper setup       # configure bot token + models"
Write-Host "  discord-helper doctor      # verify all dependencies"
Write-Host "  discord-helper run         # start the bot"
Write-Host "`nOptional (run as background service on login):"
Write-Host "  discord-helper install-service`n"
