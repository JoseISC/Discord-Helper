# Discord Helper — Windows Installation Guide

> Windows support is **experimental**. The bot core (Whisper, Ollama, TTS) works on Windows 10/11, but some rough edges may remain.

---

## Automatic Install (Recommended)

Open **PowerShell** (Windows Terminal) and run:

```powershell
iwr -useb https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.ps1 | iex
```

This will:
1. Check / install Python 3.12 via winget
2. Check / install git via winget
3. Install `pipx`
4. Clone the repo to `%LOCALAPPDATA%\discord-helper\source`
5. Download FFmpeg to `%USERPROFILE%\.local\bin\discord-helper\ffmpeg\`
6. Install `discord-helper[windows]` via pipx

---

## Manual Install

If the automatic installer fails, follow these steps:

### 1. Python 3.10+

Download from https://www.python.org/downloads/ or:

```powershell
winget install Python.Python.3.12
```

Make sure to check **"Add Python to PATH"** during installation.

### 2. git

```powershell
winget install Git.Git
```

Restart your terminal after installation.

### 3. pipx

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
```

Restart your terminal.

### 4. FFmpeg

Run the bundled script:

```powershell
.\scripts\windows\install_ffmpeg.ps1
```

Or download manually from https://ffmpeg.org/download.html and add the `bin/` folder to your PATH.

### 5. Clone and install

```powershell
git clone --branch instalador https://github.com/JoseISC/Discord-Helper.git "$env:LOCALAPPDATA\discord-helper\source"
pipx install --force "$env:LOCALAPPDATA\discord-helper\source[windows]"
```

---

## First Run

```powershell
discord-helper setup
discord-helper doctor
discord-helper run
```

---

## Background Service (Task Scheduler)

```powershell
discord-helper install-service
```

This creates a Task Scheduler task named `DiscordHelper` that runs on login.

To start immediately:

```powershell
schtasks /Run /TN DiscordHelper
```

To remove:

```powershell
discord-helper uninstall-service
```

---

## GUI Dashboard

```powershell
discord-helper gui
```

Opens `http://127.0.0.1:8750` in your browser.

---

## Logs

```powershell
discord-helper logs
# → %USERPROFILE%\.local\share\discord-helper\logs\discord-helper.log
```

---

## Common Issues

### "discord-helper not found" after install

Restart your terminal, or add the pipx path to your session:

```powershell
$env:PATH += ";$env:USERPROFILE\.local\bin"
```

### Ollama not running

Download from https://ollama.com and start it:

```powershell
ollama serve
```

### CUDA not detected

Discord Helper will automatically fall back to CPU mode. For GPU acceleration, install the NVIDIA CUDA drivers from https://developer.nvidia.com/cuda-downloads, then reinstall with:

```powershell
pipx install --force "$env:LOCALAPPDATA\discord-helper\source[windows,cuda]"
```

### FFmpeg not found after install

Add the FFmpeg `bin` directory to your PATH permanently:

```powershell
[Environment]::SetEnvironmentVariable(
    "PATH",
    "$env:PATH;$env:USERPROFILE\.local\bin\discord-helper\ffmpeg\ffmpeg-*-essentials_build\bin",
    "User"
)
```
