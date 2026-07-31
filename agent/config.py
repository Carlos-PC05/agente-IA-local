from pathlib import Path

OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen3:8b"

WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

MAX_ITERATIONS = 8
