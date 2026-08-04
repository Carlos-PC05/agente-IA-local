# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Agente de IA local (100% offline, sin llamadas a la nube) que corre contra Ollama vía su API compatible con OpenAI. Proyecto de aprendizaje: el objetivo explícito (ver `Plan.md`) es entender el bucle de agente (plan → act → observe → refine) implementado a mano en Python puro antes de delegarlo a un framework como LangGraph.

`Plan.md` es la fuente de verdad del roadmap por fases (0-6) y su checklist de progreso — consúltalo antes de proponer trabajo nuevo para saber en qué fase está el proyecto y qué es explícitamente "fuera de alcance" todavía. `docs/plans/` contiene documentos de diseño por fase (p. ej. `loop-inicial.md` para la Fase 1); no está versionado en git (ver `.gitignore`) así que es contexto local, no código.

## Comandos

Hay pytest (sin linter configurado). Los tests de las tools viven en `tests/tools/`; el resto de módulos aún usa el patrón antiguo de autochequeo inline:

```bash
# Ejecutar el REPL interactivo (requiere Ollama corriendo en localhost:11434 con el modelo cargado)
python main.py

# Tests de las tools (files, notes, shell)
pytest

# Autochequeo de un módulo aún no migrado (patrón `if __name__ == "__main__"` con asserts)
python -m agent.loop
python -m agent.tools.executor
python -m agent.tools.registry
python -m agent.tools.spec
python -m agent.tools.validation
python -m agent.audit_log
```

Los módulos de tools (`files.py`, `notes.py`, `shell.py`) ya no tienen autochequeo inline: su testing está en `tests/tools/test_*.py`, con las fixtures `workspace` y `notes_dir` de `tests/conftest.py` que redirigen los sandbox a carpetas temporales. Al añadir lógica no trivial a una tool, escribe el test ahí. Para el resto de módulos (`executor.py`, `validation.py`, etc.) la convención sigue siendo extender su propio bloque de autochequeo, que imprime `OK: <módulo> autochequeo pasado`, hasta que se migren también. La carpeta `tests/golden_tasks/` (Fase 5, aún no implementada) está reservada para tareas end-to-end de regresión contra el modelo real, no para tests unitarios.

## Arquitectura

**Flujo de una vuelta de usuario:** `main.py` (REPL) mantiene un `Memory` con el historial y llama a `agent/loop.py:run_turn()` en cada input. `run_turn()` ejecuta el ciclo plan → act → observe → refine contra el cliente `openai.OpenAI` apuntando a Ollama, hasta `MAX_ITERATIONS` vueltas:

1. **Plan**: `client.chat.completions.create(model=MODEL_NAME, messages=memory.get(), tools=tools_schema)`.
2. **Act**: si el modelo pide tool_calls, cada una se delega en `agent/tools/executor.py:execute_tool(name, raw_arguments)` — nunca se llama al handler de la tool directamente.
3. **Observe**: la llamada y su resultado se añaden a `memory` como mensajes `assistant`/`tool`.
4. **Refine**: vuelve a 1. Termina cuando el modelo responde sin tool_calls, o al agotar `MAX_ITERATIONS`.

**Capa de seguridad de tools** (`agent/tools/executor.py:execute_tool`) — punto único de ejecución, en este orden estricto:

1. Allowlist: la tool debe estar en `agent/tools/registry.py:ALL_TOOLS` (lista literal, sin registro dinámico).
2. Permiso: `tool.permission` debe estar en `agent.config.ALLOWED_PERMISSION_LEVELS` (hoy `{"read", "write", "execute"}` — `write` para `move_file` y las notas, `execute` para `run_script`).
3. Validación: argumentos parseados como JSON y validados contra el JSON Schema de la tool (`agent/tools/validation.py`, subconjunto de JSON Schema: `properties`, `required`, `enum`, `additionalProperties`).
4. Timeout: el handler corre en un `ThreadPoolExecutor` compartido con `tool.timeout_seconds` (por defecto `DEFAULT_TOOL_TIMEOUT`); un handler colgado deja de esperarse pero el hilo sigue vivo (limitación conocida, documentada en el propio `executor.py`, relevante para la futura tool de shell).

Cada llamada (éxito, rechazo o error) se registra vía `agent/audit_log.py:log_tool_call()` en `logs/tool_calls.log` (JSON Lines), con el resultado truncado a 500 caracteres. `execute_tool()` nunca lanza excepciones: cualquier fallo vuelve como string `"Error: ..."` para que el modelo lo vea y pueda reintentar.

**Definir una tool nueva** (`agent/tools/spec.py:ToolSpec`): cada módulo de tools (p. ej. `files.py`) expone una lista de `ToolSpec` (name, description, JSON Schema de parámetros, handler, `Permission`, timeout opcional). Para que sea ejecutable hay que añadirla explícitamente a `ALL_TOOLS` en `agent/tools/registry.py` — no hay autodescubrimiento. Hoy hay tres módulos de tools: `files.py` (list/read/move), `notes.py` (notas persistentes en `./notas`) y `shell.py` (`run_script`).

**Sandbox de archivos** (`agent/tools/files.py`): `list_files`/`read_file` solo pueden acceder a `WORKSPACE_DIR` (`./workspace`). `_resolve()` normaliza rutas tipo `/workspace/archivo.txt` (que algunos modelos pequeños devuelven asumiendo convención Docker) recortando ese prefijo antes de resolver, pero sigue rechazando cualquier otra ruta absoluta o cualquier `..` que escape del sandbox vía `Path.is_relative_to`.

**Ejecución de scripts** (`agent/tools/shell.py`): `run_script` reutiliza `files._resolve` (mismo sandbox) y además exige que la extensión esté en `_INTERPRETERS` (hoy solo `.py`, lanzado con `sys.executable`). Corre con `subprocess.run(shell=False)`, así que no hay inyección de comandos, y con `SCRIPT_TIMEOUT` propio (más corto que el `timeout_seconds` de la tool, para que el que salte primero sea el que sí mata al proceso hijo). Lo que el script haga una vez arrancado ya no está restringido al workspace — el sandbox cubre qué se ejecuta, no qué hace.

**Configuración central** (`agent/config.py`): `OLLAMA_BASE_URL`, `MODEL_NAME` (Qwen3 8B por defecto; hay modelos más pequeños comentados para iterar rápido en hardware limitado — sin GPU dedicada), `WORKSPACE_DIR`, `MAX_ITERATIONS`, `ALLOWED_PERMISSION_LEVELS`, `DEFAULT_TOOL_TIMEOUT`, `LOG_DIR`/`TOOL_LOG_FILE`. Es el único sitio donde se tocan estos límites.

`agent/memory.py:Memory` es deliberadamente mínima (lista de mensajes en formato OpenAI, sin persistencia) — la memoria persistente entre sesiones es Fase 4, todavía no implementada.

## Directrices de codificación

Quiero que documentes todo el código que produzcas como si trabajaras conmigo para yo entenderlo. No obstante, no quiero excesiva documentación, usa la skill /documentation-pro para realizar comentarios directos y sencillos, estilo /ponytail
