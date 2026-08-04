"""Configuracion global del agente: modelo, sandbox de archivos y limites del bucle."""
from pathlib import Path

# Endpoint local de Ollama, expuesto con API compatible con OpenAI.
OLLAMA_BASE_URL = "http://localhost:11434/v1"

#en el portátil funciona mejor "llama3.2:1b" pero es medio retrasado
MODEL_NAME = "qwen3:8b" 
#MODEL_NAME = "llama3.2:1b"  
#MODEL_NAME = "qwen2.5:1.5b"

# Unica carpeta a la que las tools de archivos pueden acceder (ver agent/tools/files.py).
WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

# Carpeta de notas persistentes del agente (ver agent/tools/notes.py). Separada
# de WORKSPACE_DIR a proposito: las notas solo se tocan via la tool de notas,
# y las tools de archivos siguen restringidas al workspace.
NOTES_DIR = Path(__file__).resolve().parent.parent / "notas"
NOTES_DIR.mkdir(exist_ok=True)

# Tope de vueltas de plan-act-observe-refine en run_turn(), para cortar bucles
# infinitos de tool-calling si el modelo no llega nunca a una respuesta final.
MAX_ITERATIONS = 8

# Niveles de permiso habilitados: una tool cuyo Permission no este en este
# conjunto se rechaza en agent/tools/executor.py antes de ejecutarla. Escritura
# habilitada para move_file y notas; ejecucion habilitada para run_script
# (agent/tools/shell.py), que solo lanza scripts de dentro del workspace.
ALLOWED_PERMISSION_LEVELS = {"read", "write", "execute"}

# Timeout por defecto (segundos) para la ejecucion de una tool, usado por
# agent/tools/executor.py cuando el ToolSpec no especifica uno propio.
DEFAULT_TOOL_TIMEOUT = 5.0

# Timeout (segundos) del subproceso que lanza agent/tools/shell.py. Es mas
# largo que DEFAULT_TOOL_TIMEOUT porque un script de usuario puede tardar, y
# la tool declara un timeout algo mayor que este para que salte primero el del
# subproceso (que si mata al proceso hijo) y no el del executor.
SCRIPT_TIMEOUT = 20.0

# Carpeta donde agent/audit_log.py escribe el registro de llamadas a tools.
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
TOOL_LOG_FILE = LOG_DIR / "tool_calls.log"
