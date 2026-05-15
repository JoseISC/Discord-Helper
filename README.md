# ⚠️ WARNING — EXPERIMENTAL PROJECT

This project was developed as a heavily vibe-coded experimental prototype.

- NOT production ready
- APIs and architecture may change at any time
- Installation flow is still unstable
- Service management is incomplete
- Security and stability have NOT been audited

Please use this repository ONLY for:

- testing
- experimentation
- development exploration
- local sandbox environments

DO NOT use this in production environments.

---

# Discord Local ASR & LLM Bot

Bot de Discord que captura audio de voz, lo transcribe localmente con **faster-whisper** (GPU NVIDIA) y responde usando un **LLM local** a través de **Ollama**.

---

## Requisitos del sistema

- Python 3.10+
- NVIDIA GPU con drivers CUDA instalados (recomendado; cae a CPU si no está disponible)
- [Ollama](https://ollama.com/) corriendo en `localhost:11434`
- FFmpeg instalado y en el PATH del sistema
