# Discord Helper — Installer & Packaging Refactor Prompt

Necesito transformar este repositorio Python de bot de Discord en una aplicación instalable tipo Ollama para Linux y macOS.

## Contexto actual

- Repo: Discord-Helper
- Entry point actual: `main.py`
- Usa `discord.py`, `faster-whisper`, `Ollama`, TTS con `transformers`, FFmpeg y variables en `.env`.
- El bot se conecta a Discord, escucha audio, transcribe con Whisper, consulta un modelo local por Ollama y responde por texto o voz.
- Actualmente se ejecuta manualmente con `python main.py`.

## Objetivo

Crear una experiencia de instalación y uso tipo:

```bash
curl -fsSL https://discord-helper.app/install.sh | sh
```

Y luego:

```bash
discord-helper setup
discord-helper doctor
discord-helper run
discord-helper install-service
discord-helper logs
```

## Tareas

1. Reestructurar el proyecto como paquete Python instalable.
2. Crear `pyproject.toml` con entry point:

```toml
[project.scripts]
discord-helper = "discord_helper.cli:app"
```

3. Mover el código desde `src/` y `main.py` hacia un paquete `discord_helper/`.
4. Crear un CLI usando Typer o Click.
5. Implementar:
   - `discord-helper setup`
   - `discord-helper run`
   - `discord-helper doctor`
   - `discord-helper install-service`
   - `discord-helper uninstall-service`
   - `discord-helper logs`
6. Cambiar la configuración para leer desde:

```bash
~/.config/discord-helper/config.env
```

Y permitir override por variables de entorno.

7. No hacer `sys.exit()` al importar config. La validación debe ocurrir al ejecutar `run` o `doctor`.
8. Separar dependencias base, CUDA y desarrollo.
9. Crear soporte básico para Linux `systemd --user`.
10. Crear soporte básico para macOS `launchd`.
11. Crear `scripts/install.sh` para instalación tipo:

```bash
curl -fsSL URL | bash
```

12. Actualizar README con instalación para usuario final.
13. Agregar una guía para crear el bot en Discord Developer Portal, configurar token, intents y link de invitación.
14. Mantener compatibilidad con el flujo actual de comandos Discord:
   - `/join`
   - `/leave`
   - `/ask`
   - `/start`
   - `/stop`
15. Agregar logs claros y comando `doctor` que revise:
   - Python
   - FFmpeg
   - Ollama disponible
   - modelo Ollama existe
   - token Discord configurado
   - dependencias ASR
   - dependencias TTS

## Arquitectura sugerida

```text
Discord-Helper/
├── pyproject.toml
├── discord_helper/
│   ├── __init__.py
│   ├── cli.py
│   ├── runtime.py
│   ├── config_loader.py
│   ├── asr.py
│   ├── llm.py
│   ├── tts.py
│   ├── audio.py
│   ├── sink.py
│   └── cogs/
├── scripts/
│   └── install.sh
├── docs/
│   └── discord-setup.md
└── README.md
```

## Restricciones

- No commitear tokens.
- No guardar `.env` en el repo.
- Mantener soporte Linux y macOS.
- En macOS no depender de CUDA.
- En Linux permitir instalación CPU por defecto y CUDA como extra opcional.
- Mantener el código modular.

## Extras recomendados

- Comando `discord-helper version`
- Comando `discord-helper update`
- Detección automática de Ollama local
- Descarga automática de modelos Whisper pequeños
- Logs persistentes en:

```bash
~/.local/share/discord-helper/logs/
```

- Configuración persistente en:

```bash
~/.config/discord-helper/
```

- Generación automática de archivos `systemd` o `launchd`
- Instalación mediante `pipx`
- Soporte futuro para Windows
