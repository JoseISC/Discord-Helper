# Sprint 2 — Servicios y Persistencia

## Nuevas funcionalidades

### Logs persistentes

Los logs ahora se almacenan en:

~/.local/share/discord-helper/logs/

Archivo principal:

- discord-helper.log

---

## Instalación servicio local

### Linux

Comando:

- discord-helper install-service

Genera:

- ~/.config/systemd/user/discord-helper.service

---

### macOS

Comando:

- discord-helper install-service

Genera:

- ~/Library/LaunchAgents/com.discord-helper.plist

---

## Remover servicio

Comando:

- discord-helper uninstall-service

---

## Logs

Comando:

- discord-helper logs

---

## Mejoras runtime

- graceful shutdown
- signal handling
- persistent logging
- runtime manager
