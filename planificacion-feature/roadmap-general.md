# Roadmap General — Discord Helper Installer

## Visión

Crear una experiencia tipo Ollama para ejecutar asistentes de Discord locales impulsados por Whisper y Ollama.

El usuario debería poder:

```bash
discord-helper setup
discord-helper doctor
discord-helper run
```

Sin necesidad de configurar manualmente entornos Python.

---

# Épicas principales

## EPIC-01 — Reestructuración del proyecto

Migrar desde estructura script-based hacia paquete instalable.

## EPIC-02 — CLI multiplataforma

Crear interfaz de línea de comandos para usuarios finales.

## EPIC-03 — Configuración persistente

Desacoplar configuración del repositorio.

## EPIC-04 — Runtime y servicios

Permitir ejecución persistente como servicio local.

## EPIC-05 — Instalador automático

Implementar experiencia tipo curl | bash.

## EPIC-06 — Experiencia usuario

Mejorar onboarding Discord y diagnóstico.

---

# Resultado esperado final

## Linux

```bash
curl -fsSL https://discord-helper.app/install.sh | sh

discord-helper setup
discord-helper run
```

## macOS

```bash
brew install discord-helper

discord-helper setup
discord-helper run
```

---

# Métricas de éxito

- Instalación completa < 5 minutos
- Setup completo < 3 minutos
- Usuario sin conocimientos Python puede usarlo
- Compatibilidad Linux y macOS
- Configuración persistente
- Logs persistentes
- CLI estable
