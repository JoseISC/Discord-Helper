# Sprint 2 — Servicios y persistencia

## Objetivo

Permitir que Discord Helper funcione como servicio persistente local.

## Duración

2 semanas

---

# Épicas

- EPIC-03
- EPIC-04

---

# Historias incluidas

- HU-04
- HU-06

---

# Tasks

## Runtime

- Manejo lifecycle bot
- Graceful shutdown
- Logs persistentes

## Linux

- Crear templates systemd
- Instalar servicio user
- Start/stop service

## macOS

- Crear launchd plist
- Instalar launchctl
- Start/stop launchctl

## Logs

- Crear carpeta logs persistentes
- Implementar rotación básica logs

## CLI

- Implementar install-service
- Implementar uninstall-service
- Implementar logs

---

# Resultado esperado

Usuario puede:

```bash
discord-helper install-service
discord-helper logs
```

Y el bot inicia automáticamente.
