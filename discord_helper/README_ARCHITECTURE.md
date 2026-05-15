# Discord Helper Installer Branch

Esta rama representa una primera aproximación para transformar Discord-Helper desde un script Python ejecutado manualmente hacia una aplicación instalable tipo Ollama.

## Objetivos de esta rama

- Crear una estructura instalable.
- Separar runtime, configuración y CLI.
- Preparar soporte para Linux y macOS.
- Centralizar configuración fuera del repositorio.
- Facilitar futuros instaladores automáticos.

## Estructura objetivo

```text
Discord-Helper/
├── pyproject.toml
├── discord_helper/
│   ├── __init__.py
│   ├── cli.py
│   ├── runtime.py
│   ├── config_loader.py
│   └── services/
├── scripts/
│   └── install.sh
└── docs/
```

## Comandos esperados

```bash
discord-helper setup
discord-helper doctor
discord-helper run
discord-helper install-service
discord-helper logs
```

## Dirección técnica

### Configuración

La configuración debería migrar desde `.env` dentro del repo hacia:

```bash
~/.config/discord-helper/config.env
```

### Servicios

Linux:
- systemd --user

macOS:
- launchd

### Instalación

Instalación tipo:

```bash
curl -fsSL URL | bash
```

### Dependencias

Separar:

- base
- cpu
- cuda
- dev

## Próximos pasos

1. Crear `pyproject.toml`
2. Crear CLI con Typer
3. Migrar `main.py` hacia `runtime.py`
4. Implementar `setup`
5. Implementar `doctor`
6. Agregar instalación systemd
7. Agregar instalación launchd
8. Crear install.sh
