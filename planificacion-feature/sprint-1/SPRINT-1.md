# Sprint 1 — Base instalable y CLI

## Objetivo

Transformar el proyecto en paquete instalable y crear CLI funcional mínima.

## Duración

2 semanas

---

# Épicas

- EPIC-01
- EPIC-02

---

# Historias incluidas

- HU-01
- HU-02
- HU-03

---

# Tasks

## Arquitectura

- Crear pyproject.toml
- Crear estructura discord_helper/
- Migrar main.py a runtime.py
- Crear __init__.py

## CLI

- Instalar Typer
- Crear comando setup
- Crear comando run
- Crear comando doctor

## Configuración

- Crear config_loader.py
- Implementar lectura ~/.config/discord-helper/

## Validaciones

- Detectar Python
- Detectar ffmpeg
- Detectar Ollama

---

# Resultado esperado

Usuario puede:

```bash
discord-helper setup
discord-helper doctor
discord-helper run
```
