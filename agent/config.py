"""Configuracion global del agente: modelo, sandbox de archivos y limites del bucle."""
from pathlib import Path

# Endpoint local de Ollama, expuesto con API compatible con OpenAI.
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen3:8b"

# Unica carpeta a la que las tools de archivos pueden acceder (ver agent/tools/files.py).
WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

# Tope de vueltas de plan-act-observe-refine en run_turn(), para cortar bucles
# infinitos de tool-calling si el modelo no llega nunca a una respuesta final.
MAX_ITERATIONS = 8
