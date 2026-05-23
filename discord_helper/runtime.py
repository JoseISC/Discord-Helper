"""Bot runtime manager — ejecuta AmlaBot in-process."""

from __future__ import annotations

import asyncio
import logging
import os

from .config_loader import load_config
from .logging_utils import configure_logging

logger = logging.getLogger(__name__)


def run_bot() -> None:
    """Carga la config, valida vars requeridas y arranca el bot in-process."""
    load_config()
    configure_logging()

    # Refresca las variables del módulo core.config ahora que el .env del usuario
    # ya fue cargado por load_config().
    from discord_helper.core.config import load_runtime_config

    try:
        load_runtime_config()
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    # Importar y arrancar el bot en el mismo proceso — sin subprocess.
    from discord_helper.bot import main

    asyncio.run(main())
