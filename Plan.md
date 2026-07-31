# Plan de Proyecto: Agente de IA Local y Ligero

## Objetivo

Construir un agente de IA que corre 100% en local (sin llamadas a la nube), capaz de ayudar en tareas sencillas del día a día en el ordenador (gestión de archivos, notas, automatizaciones cortas), como proyecto práctico para mejorar habilidades de desarrollo backend e ingeniería de IA.

## Contexto técnico

- **Sistema operativo:** Windows
- **Hardware:** Sin GPU dedicada, 16GB de RAM
- **Runtime de inferencia:** Ollama (`http://localhost:11434/v1`, API compatible con OpenAI)
- **Modelo inicial:** Qwen3 8B (cuantizado Q4) — buen equilibrio entre tool-calling y consumo de recursos en CPU
- **Modelo de respaldo para desarrollo rápido:** Phi-3 Mini (~2GB) — usar solo para probar el bucle/tools mientras se itera, no para evaluar calidad final
- **Framework del bucle:** Python puro (sin LangGraph, de momento) — prioridad de aprendizaje: entender el bucle plan → act → observe → refine antes de delegarlo a un framework

## Principio de diseño

> Empezar con un bucle de agente estricto y tools pequeñas y seguras. Escalar a orquestación con frameworks (LangGraph) solo cuando lo básico funcione de forma fiable.

### Arquitectura del Bucle en Python

El núcleo de un agente autónomo almacena un historial de mensajes o estado que se actualiza en cada iteración del bucle.

- Plan: El modelo analiza el objetivo actual y decide el siguiente paso o herramienta a utilizar.
- Act: Se ejecuta la función o herramienta seleccionada con los argumentos provistos.
- Observe: Se captura el resultado devuelto por la herramienta o el entorno.
- Refine: El agente evalúa si el resultado es satisfactorio o si necesita ajustar el rumbo antes de continuar o finalizar.

## Estructura del proyecto

```
local-agent/
├── agent/
│   ├── loop.py          # bucle plan → act → observe → refine
│   ├── tools/
│   │   ├── files.py      # leer/mover/renombrar archivos
│   │   ├── shell.py       # comandos permitidos (allowlist estricta)
│   │   └── notes.py       # notas/recordatorios locales
│   ├── memory.py         # historial de conversación + estado persistente
│   └── config.py         # modelo, límites, permisos
├── tests/
│   └── golden_tasks/     # tareas fijas para evaluar regresiones
└── main.py
```

## Fases del proyecto

### Fase 0 — Preparación del entorno

- [x] Instalar Ollama para Windows
- [x] Ejecutar `ollama pull qwen3:8b`
- [x] Verificar que el modelo responde correctamente en `http://localhost:11434/v1`
- [x] Configurar entorno Python (venv) para el proyecto

### Fase 1 — MVP: bucle + una tool

- [x] Implementar el bucle básico (plan → act → observe → refine) en `loop.py`
- [x] Implementar una única tool: listar/leer archivos de una carpeta
- [ ] Probar el flujo de extremo a extremo: petición del usuario → el modelo decide usar la tool → se ejecuta → el resultado vuelve al modelo → respuesta final (pendiente: requiere Ollama corriendo con el modelo cargado)
- [ ] Medir latencia real en tu hardware (CPU) para calibrar expectativas (pendiente: requiere Ollama corriendo)

### Fase 2 — Seguridad de herramientas

- [ ] Definir una allowlist explícita de comandos/acciones permitidas
- [ ] Validar los argumentos de cada tool con JSON Schema antes de ejecutarlos
- [ ] Añadir niveles de permiso (ej: lectura vs escritura vs ejecución)
- [ ] Forzar timeouts en cada llamada a herramienta
- [ ] Registrar (log) cada llamada a tool: qué se pidió, qué argumentos, qué resultado

### Fase 3 — Ampliación de capacidades

- [ ] Tool de organización de archivos (mover/renombrar según reglas)
- [ ] Tool de notas/recordatorios locales persistentes
- [ ] Tool de ejecución de scripts propios (con allowlist estricta)
- [ ] (Opcional, conecta con tu interés en RAG) Tool de búsqueda semántica sobre tus propios documentos locales

### Fase 4 — Memoria

- [ ] Memoria de sesión: contexto de la tarea actual (se descarta al terminar)
- [ ] Memoria persistente: preferencias del usuario y tareas recurrentes (se guarda entre sesiones)
- [ ] Definir explícitamente qué se guarda y qué no (límites de privacidad/tamaño)

### Fase 5 — Evaluación

- [ ] Crear un conjunto fijo de "golden tasks": tareas de prueba con resultado esperado conocido
- [ ] Ejecutar el conjunto tras cada cambio relevante para detectar regresiones
- [ ] Documentar métricas básicas: % de tareas resueltas correctamente, latencia media

### Fase 6 — Evolución (opcional)

- [ ] Migrar el bucle a LangGraph si se necesitan checkpoints/reintentos robustos
- [ ] Evaluar subir de modelo (Qwen3 30B-A3B o similar) si el hardware lo permite en el futuro
- [ ] Explorar integración con MCP para reutilizar tools estándar del ecosistema

## Próximo paso inmediato

Completar la Fase 0 e implementar el MVP de la Fase 1 con una sola tool, para validar que el bucle completo funciona antes de añadir complejidad.
