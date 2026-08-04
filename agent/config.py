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

# Tope de vueltas de plan-act-observe-refine en run_turn(), para cortar bucles
# infinitos de tool-calling si el modelo no llega nunca a una respuesta final.
MAX_ITERATIONS = 8

# Niveles de permiso habilitados: una tool cuyo Permission no este en este
# conjunto se rechaza en agent/tools/executor.py antes de ejecutarla. Escritura
# habilitada para move_file (Fase 3); ejecucion se habilita aqui explicitamente
# cuando llegue la tool de shell.
ALLOWED_PERMISSION_LEVELS = {"read", "write"}

# Timeout por defecto (segundos) para la ejecucion de una tool, usado por
# agent/tools/executor.py cuando el ToolSpec no especifica uno propio.
DEFAULT_TOOL_TIMEOUT = 5.0

# Carpeta donde agent/audit_log.py escribe el registro de llamadas a tools.
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
TOOL_LOG_FILE = LOG_DIR / "tool_calls.log"
