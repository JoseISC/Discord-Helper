# ⚠️ WARNING — EXPERIMENTAL PROJECT

This project was developed as a heavily vibe-coded experimental prototype.

- NOT production ready
- APIs and architecture may change at any time
- Installation flow is still unstable
- Service management is incomplete
- Security and stability have NOT been audited

Please use this repository ONLY for:

- testing
- experimentation
- development exploration
- local sandbox environments

DO NOT use this in production environments.

Spanish documentation is available in:

- docs/es/

---

# Discord Local ASR & LLM Bot

Discord bot that captures voice audio, transcribes it locally using faster-whisper, and responds using a local LLM through Ollama.

---

# Features

- Local speech-to-text using Whisper
- Local LLM responses using Ollama
- Voice channel interaction
- Text chat interaction
- Text-to-speech responses
- Installable CLI workflow
- Linux and macOS support

---

# Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.sh | bash
```

---

# Initial Setup

Run:

```bash
discord-helper setup
```

Then validate installation:

```bash
discord-helper doctor
```

Finally run the bot:

```bash
discord-helper run
```

---

# Service Installation

Optional background service installation:

```bash
discord-helper install-service
```

---

# Logs

```bash
discord-helper logs
```

Persistent logs are stored in:

```text
~/.local/share/discord-helper/logs/
```

---

# Discord Setup Guide

```bash
discord-helper discord-guide
```

Or see:

- docs/discord-setup.md

---

# Current Status

## Sprint 1

- Installable package
- CLI
- Persistent config
- Runtime wrapper
- Environment diagnostics

## Sprint 2

- Persistent logs
- Runtime manager
- Graceful shutdown
- systemd support
- launchd support
- Service installation

## Sprint 3

- install.sh bootstrap installer
- Linux/macOS onboarding
- Discord onboarding
- User documentation

---

# Supported Platforms

- Linux
- macOS (experimental)

---

# License

Experimental open-source project.
