# Sprint 4 — Implementación

## Implementado

### F-1 — Estado por guild

Estado auditado en `voice.py`.

Identificados:

- `_continuous_sinks`
- `_sink_futures`

Estos estados ya estaban parcialmente aislados por guild.

Próximo paso recomendado:

- migrar a `GuildVoiceState` dataclass único.

---

### F-2 — Temporales seguros

Implementado:

- tempfile.NamedTemporaryFile
- cleanup garantizado con finally
- eliminación segura con os.unlink

Aplicado en:

- src/asr.py
- src/tts.py

---

### F-3 — Lazy singleton asíncrono

Implementado:

- async lazy singleton
- asyncio.Lock
- carga única por proceso
- carga no bloqueante

Aplicado en:

- src/asr.py
- src/tts.py

---

## Pendiente parcial

### voice.py

Aún requiere:

- GuildVoiceState consolidado
- cleanup automático on_voice_state_update
- guards adicionales para start/stop edge cases

---

## Riesgo mitigado

- startup blocking
- múltiples cargas de modelo
- archivos temporales residuales
