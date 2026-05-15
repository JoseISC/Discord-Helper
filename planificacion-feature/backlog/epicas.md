# Épicas — Instalador Discord Helper

# EPIC-01 — Proyecto instalable

## Objetivo
Transformar el proyecto actual hacia un paquete Python instalable.

## Entregables
- pyproject.toml
- entrypoint CLI
- estructura modular
- runtime desacoplado

---

# EPIC-02 — CLI oficial

## Objetivo
Crear experiencia CLI estable.

## Comandos
- setup
- doctor
- run
- logs
- install-service
- uninstall-service
- update

---

# EPIC-03 — Configuración persistente

## Objetivo
Mover configuración fuera del repositorio.

## Entregables
- ~/.config/discord-helper/
- config.env
- config validation
- override por env vars

---

# EPIC-04 — Servicios locales

## Objetivo
Soporte para ejecución persistente.

## Linux
- systemd --user

## macOS
- launchd

---

# EPIC-05 — Instalador automático

## Objetivo
Crear experiencia de instalación simplificada.

## Entregables
- install.sh
- detección OS
- instalación ffmpeg
- instalación dependencias
- instalación pipx

---

# EPIC-06 — Diagnóstico y soporte

## Objetivo
Facilitar troubleshooting.

## Entregables
- comando doctor
- validación Ollama
- validación Discord token
- validación FFmpeg
- logs persistentes
