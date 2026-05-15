# Agente de Planificación — Sprint 4 & 5: Corrección de Fracturas Arquitectónicas

## Discord Local ASR & LLM Bot

---

## Contexto del proyecto

Eres un **Senior Software Engineer** especializado en Python asíncrono, discord.py 2.x,
y sistemas de IA local (faster-whisper, Ollama, HuggingFace Transformers).

El repositorio es `Discord-Helper`, un bot de Discord que captura audio de voz por canal,
lo transcribe localmente con **faster-whisper** (GPU NVIDIA / fallback CPU), lo procesa
con un **LLM local vía Ollama**, y reproduce la respuesta sintetizada con **TTS**
(`facebook/mms-tts-spa`). El stack es 100 % local: sin APIs externas.

## Estructura actual del repositorio

```text
Discord-Helper/
├── .env / .env.example
├── Modelfile              # Definición del modelo gemma-aggressive en Ollama
├── main.py                # Entry point — AmlaBot(commands.Bot), carga cogs
├── prompt.md              # Prompt original del agente de construcción
├── requirements.txt
└── src/
    ├── config.py          # Carga/validación de variables de entorno
    ├── asr.py             # Motor STT — faster-whisper
    ├── llm.py             # Cliente Ollama asíncrono
    ├── tts.py             # Motor TTS — facebook/mms-tts-spa
    ├── audio.py           # Reproducción de audio — FFmpegPCMAudio
    ├── sink.py            # WaveSink para captura de voz
    └── cogs/
        ├── voice.py       # Slash commands: /join /leave /ask /start /stop
        └── chat.py        # Slash commands: /chat, menciones de texto
```

---

## Fracturas identificadas

| ID | Fractura | Severidad | Sprint |
|---|---|---|---|
| F-1 | Estado compartido sin aislamiento por guild | Alta | 4 |
| F-2 | Archivos temporales sin limpieza garantizada | Alta | 4 |
| F-3 | Carga de modelos bloqueante al inicio | Media | 4 |
| F-4 | Sin historial de conversación por sesión | Media | 5 |
| F-5 | Sanitización de salida LLM incompleta | Baja | 5 |

---

# SPRINT 4 — Estabilidad y corrección de estado

## Objetivo

Hacer el bot funcionalmente correcto en escenarios multi-servidor y libre de resource leaks.

---

## F-1 — Estado compartido sin aislamiento por guild

### Problema

El cog `voice.py` puede mantener estado mutable como atributos de instancia. Como el cog es una instancia única, este estado queda compartido entre servidores.

### Tareas

1. Explorar `src/cogs/voice.py` e identificar cada atributo de estado mutable.
2. Crear estado por guild:

```python
from dataclasses import dataclass, field

@dataclass
class GuildVoiceState:
    recording: bool = False
    active_sink: WaveSink | None = None
    audio_buffer: list[bytes] = field(default_factory=list)
```

3. Reemplazar accesos a atributos globales por `self._guild_state[guild_id]`.
4. Agregar cleanup en `on_voice_state_update` cuando el bot sea desconectado.
5. Validar `/start` duplicado y `/stop` sin `/start`.

### Criterios de aceptación

- El bot puede estar en dos servidores simultáneamente sin interferencia.
- `/stop` de un servidor no interrumpe otro servidor.
- No quedan atributos mutables de instancia fuera del diccionario de estado.

---

## F-2 — Archivos temporales sin limpieza garantizada

### Problema

El pipeline STT → TTS puede dejar archivos `.wav` temporales si ocurre una excepción.

### Tareas

1. Auditar `sink.py`, `asr.py`, `tts.py` y `audio.py`.
2. Migrar creación de temporales a `tempfile`.
3. Usar `delete=False` cuando FFmpeg deba leer el archivo después del cierre.
4. Limpiar archivos con `finally`.
5. Asegurar cleanup ante `/leave` abrupto.

### Patrón esperado

```python
import tempfile
import os

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    tmp_path = f.name
    f.write(audio_data)

try:
    result = await asyncio.to_thread(transcribe, tmp_path)
finally:
    os.unlink(tmp_path)
```

### Criterios de aceptación

- Ningún `.wav` temporal queda en disco después de ejecución exitosa o fallida.
- No hay rutas hardcodeadas como `output.wav` o `recording.wav`.
- Cleanup cubierto por `finally` o context managers.

---

## F-3 — Carga de modelos bloqueante al inicio

### Problema

La carga de modelos STT/TTS puede bloquear startup o generar latencia oculta en el primer comando.

### Tareas

1. Verificar cuándo se instancian modelos en `asr.py` y `tts.py`.
2. Implementar lazy singleton con lock asíncrono.
3. Cargar modelos en background desde `setup_hook` en `main.py`.
4. Aplicar patrón en `asr.py` y `tts.py`.
5. En `/ask` y `/stop`, usar `await asr.get_model()` y equivalente TTS.

### Patrón esperado

```python
_model: WhisperModel | None = None
_model_lock = asyncio.Lock()

async def get_model() -> WhisperModel:
    global _model
    if _model is not None:
        return _model
    async with _model_lock:
        if _model is None:
            _model = await asyncio.to_thread(_load_model)
    return _model
```

### Criterios de aceptación

- Comandos básicos responden en menos de 2 segundos desde el inicio.
- El modelo se carga una sola vez por proceso.
- Llamadas concurrentes no crean múltiples instancias.

---

# SPRINT 5 — Calidad de conversación y robustez de salida

## Objetivo

Mejorar coherencia conversacional y eliminar artefactos de texto en salida TTS.

---

## F-4 — Sin historial de conversación por sesión

### Problema

`llm.py` trata cada prompt como una interacción aislada, sin memoria por servidor.

### Tareas

1. Agregar `history` a `GuildVoiceState`.
2. Modificar `llm.ask()` para aceptar historial.
3. Guardar pares user/assistant después de cada respuesta.
4. Implementar ventana de contexto.
5. Agregar comando `/clear` para limpiar historial del guild.

### Patrón esperado

```python
MAX_HISTORY_TURNS = 10

def trim_history(history: list[dict]) -> list[dict]:
    return history[-(MAX_HISTORY_TURNS * 2):]
```

### Criterios de aceptación

- La conversación mantiene contexto por servidor.
- El historial no crece indefinidamente.
- `/clear` limpia historial y confirma con mensaje efímero.
- El historial es independiente por guild.

---

## F-5 — Sanitización de salida LLM incompleta

### Problema

`strip_markdown()` no elimina todos los artefactos que dañan el TTS: URLs, emojis, listas, código y frases meta.

### Tareas

1. Crear `src/text_utils.py` con `sanitize_for_tts()`.
2. Reemplazar `strip_markdown()` por `sanitize_for_tts()` en voz.
3. Agregar instrucción anti-markdown al system prompt en `llm.py`.
4. Crear tests unitarios en `tests/test_text_utils.py`.

### Implementación esperada

```python
import re

def sanitize_for_tts(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
```

### Criterios de aceptación

- TTS no recibe backticks, asteriscos, números de lista ni URLs.
- `sanitize_for_tts` tiene tests unitarios.
- El prompt reduce artefactos del modelo.

---

# Instrucciones de trabajo

## Fase 1 — Exploración

1. Leer completamente `main.py`, `src/config.py` y ambos cogs.
2. Leer `src/asr.py`, `src/tts.py`, `src/llm.py`, `src/sink.py` y `src/audio.py`.
3. Confirmar cada fractura antes de modificar.
4. Mapear dependencias: F-1 debe completarse antes de F-4.

## Fase 2 — Implementación por fractura

Trabajar en orden:

1. F-1
2. F-2
3. F-3
4. F-4
5. F-5

Para cada fractura:

- Revisar diff antes de aplicar.
- Explicar en comentarios de código el motivo del cambio.
- Verificar que el bot arranca.

## Fase 3 — Verificación transversal

### Al completar Sprint 4

- El bot inicia.
- Se une a canal.
- Graba.
- Transcribe.
- Reproduce TTS.
- No deja archivos temporales residuales.

### Al completar Sprint 5

- Conversación de 3 turnos mantiene contexto.
- Salida TTS no contiene artefactos markdown.

---

# Restricciones

- No cambiar API pública sin actualizar callsites.
- No agregar dependencias sin `requirements.txt`.
- Mantener fallback CUDA → CPU.
- No tocar `Modelfile`, `prompt.md` ni docs existentes salvo indicación explícita.

---

# Entregables esperados

## Sprint 4

- `src/cogs/voice.py` — estado aislado por guild con `GuildVoiceState`
- `src/asr.py` — lazy singleton con lock asíncrono
- `src/tts.py` — lazy singleton con lock asíncrono
- `src/sink.py` + `src/audio.py` — temporales con `tempfile` + `finally`
- `main.py` — carga de modelos en background en `setup_hook`

## Sprint 5

- `src/llm.py` — historial con ventana deslizante
- `src/cogs/voice.py` — historial por guild + `/clear`
- `src/text_utils.py` — `sanitize_for_tts`
- `tests/test_text_utils.py` — tests unitarios
- `llm.py` o `Modelfile` — instrucción anti-markdown
