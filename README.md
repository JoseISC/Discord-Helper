# Discord Local ASR & LLM Bot

Bot de Discord que captura audio de voz, lo transcribe localmente con **faster-whisper** (GPU NVIDIA) y responde usando un **LLM local** a través de **Ollama**.

---

## Requisitos del sistema

- Python 3.10+
- NVIDIA GPU con drivers CUDA instalados (recomendado; cae a CPU si no está disponible)
- [Ollama](https://ollama.com/) corriendo en `localhost:11434`
- FFmpeg instalado y en el PATH del sistema

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd Discord-Helper
```

### 2. Crear y activar entorno virtual

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

> Para soporte CUDA completo en `faster-whisper`, instala también:
> ```bash
> pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
> ```

> Para que el modelo TTS use la GPU (opcional, recomendado si tienes ≥ 8 GB VRAM),
> instala PyTorch con soporte CUDA desde [pytorch.org](https://pytorch.org/get-started/locally/).
> Si la VRAM es ajustada con Whisper cargado, usa `TTS_FORCE_CPU=1` en tu `.env`.

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena los valores:

```env
DISCORD_TOKEN=tu_token_aqui
OLLAMA_MODEL=llama3
```

### 5. Modelo Ollama

**Opción A — modelo genérico**

```bash
ollama pull llama3
```

En `.env`, usa por ejemplo `OLLAMA_MODEL=llama3`.

**Opción B — modelo definido en el repositorio (`Modelfile`)**

Este proyecto incluye un `Modelfile` que crea el modelo local `gemma-aggressive` (Ollama descargará la imagen base indicada en el archivo la primera vez que haga falta):

```bash
ollama create gemma-aggressive -f Modelfile
```

En `.env`, establece `OLLAMA_MODEL=gemma-aggressive`.

---

## Uso

```bash
python main.py
```

### Comandos disponibles en Discord

| Comando | Descripción |
|---------|-------------|
| `/join` | El bot se une a tu canal de voz |
| `/leave` | El bot abandona el canal de voz |
| `/ask [segundos]` | Graba tu voz N segundos, transcribe y consulta el LLM (responde en texto) |
| `/start` | El bot empieza a escucharte de forma continua |
| `/stop` | Detiene la escucha y ejecuta el pipeline completo: STT → LLM → TTS → reproduce la respuesta por voz en el canal |

#### Flujo de voz interactiva

1. Únete a un canal de voz y usa `/start`.
2. Habla con normalidad (sin límite de tiempo).
3. Usa `/stop` cuando hayas terminado tu pregunta.
4. El bot transcribe tu voz, consulta el LLM y responde hablando en el canal.
5. Para volver a preguntar, usa `/start` de nuevo (el bot se queda en el canal).
6. Cuando termines, usa `/leave` para que el bot se desconecte.

---

## Variables de entorno

| Variable | Requerida | Descripción | Por defecto |
|----------|-----------|-------------|-------------|
| `DISCORD_TOKEN` | Sí | Token del bot de Discord | — |
| `OLLAMA_MODEL` | Sí | Modelo Ollama a usar (ej: `llama3`, `mistral`) | — |
| `OLLAMA_HOST` | No | URL del servidor Ollama | `http://localhost:11434` |
| `WHISPER_MODEL` | No | Tamaño del modelo Whisper | `medium` |
| `ASR_LANGUAGE` | No | Idioma forzado (`es`, `en`) o vacío para auto-detección | auto |
| `TTS_MODEL` | No | Modelo TTS de Hugging Face para síntesis de voz | `facebook/mms-tts-spa` |
| `TTS_FORCE_CPU` | No | Establece `1` para forzar el TTS a CPU (ahorra VRAM) | desactivado |

### Modelos Whisper disponibles

| Modelo | VRAM aprox. | Velocidad |
|--------|-------------|-----------|
| `tiny` | ~1 GB | Muy rápido |
| `base` | ~1 GB | Rápido |
| `small` | ~2 GB | Bueno |
| `medium` | ~5 GB | Recomendado |
| `large-v3` | ~10 GB | Máxima precisión |

---

## Estructura del proyecto

```
Discord-Helper/
├── .env                   # Variables de entorno (no commitear)
├── .env.example           # Plantilla de variables de entorno
├── Modelfile              # Definición Ollama para `gemma-aggressive` (ver instalación, opción B)
├── requirements.txt
├── main.py                # Entry point
└── src/
    ├── config.py          # Carga y validación de configuración
    ├── asr.py             # Motor de transcripción (faster-whisper)
    ├── llm.py             # Cliente Ollama asíncrono + prompts de voz
    ├── tts.py             # Motor TTS (facebook/mms-tts-spa via Transformers)
    ├── audio.py           # Reproducción de audio en canal de voz (FFmpegPCMAudio)
    ├── sink.py            # WaveSink para captura de audio
    └── cogs/
        ├── voice.py       # Slash commands de voz (/join, /leave, /ask, /start, /stop)
        └── chat.py        # Slash commands de texto (/chat, menciones)
```

---

## Permisos necesarios para el bot en Discord

En el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications):

- **Bot Permissions:** `Connect`, `Speak`, `Send Messages`, `Use Slash Commands`
- **Privileged Intents:** `Server Members Intent` (opcional), `Voice States`

---

## Solución de problemas

**El bot no transcribe nada:**
- Asegúrate de hablar en el canal de voz durante la grabación.
- Verifica que el micrófono esté configurado correctamente en Discord.

**Error de CUDA:**
- Verifica que los drivers NVIDIA estén instalados: `nvidia-smi`
- El bot caerá automáticamente a CPU si CUDA no está disponible.

**Ollama no responde:**
- Verifica que el servidor esté corriendo: `ollama serve`
- Comprueba que el modelo esté descargado: `ollama list`

**El TTS falla al cargar el modelo:**
- La primera vez se descarga `facebook/mms-tts-spa` (~400 MB) desde Hugging Face. Requiere conexión a internet.
- Si la VRAM es insuficiente, establece `TTS_FORCE_CPU=1` en el `.env`.

**El bot no reproduce audio (FFmpeg):**
- Verifica que `ffmpeg` esté instalado y en el PATH: `ffmpeg -version`
- En Pop!_OS/Ubuntu: `sudo apt install ffmpeg`

**Las respuestas de voz contienen ruido (asteriscos, guiones...):**
- Cambia a un modelo Ollama que siga mejor instrucciones de sistema, o reduce la temperatura del modelo.
- El sistema ya aplica `strip_markdown()` como segunda defensa.
