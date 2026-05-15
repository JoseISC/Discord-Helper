# Sprint 1 — Uso Inicial

## Instalación desarrollo

```bash
pip install -e .
```

## Comandos disponibles

```bash
discord-helper setup
discord-helper doctor
discord-helper run
```

## Configuración persistente

La configuración se guarda en:

```bash
~/.config/discord-helper/config.env
```

## Diagnóstico

El comando doctor revisa:

- Python
- FFmpeg
- Ollama
- Variables requeridas

## Estado actual

Sprint 1 implementa:

- CLI básica
- paquete instalable
- configuración persistente
- runtime wrapper
- validaciones iniciales
