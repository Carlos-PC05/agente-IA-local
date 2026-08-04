"""Tool de ejecucion de scripts propios del workspace, con allowlist estricta."""
import subprocess
import sys

from agent.config import SCRIPT_TIMEOUT
from agent.tools.files import _resolve
from agent.tools.spec import Permission, ToolSpec

# Allowlist estricta: extension de script -> comando base con el que lanzarlo.
# Solo se ejecuta lo que esta aqui; cualquier otra extension se rechaza. Se usa
# sys.executable (el Python del venv actual) en vez de "python" para no depender
# del PATH del sistema.
_INTERPRETERS = {".py": [sys.executable]}
_MAX_OUTPUT = 2000


def run_script(script: str, args: list[str] | None = None) -> str:
    """Ejecuta un script del workspace y devuelve su codigo de salida y su salida.

    Doble restriccion: la ruta se resuelve con el mismo sandbox que las tools
    de archivos (agent/tools/files.py:_resolve, reutilizado a proposito para
    tener una sola definicion de "dentro del workspace"), y la extension debe
    estar en la allowlist _INTERPRETERS. El script se lanza sin shell
    (shell=False), asi que los argumentos se pasan literales y no hay inyeccion
    de comandos posible.

    ponytail: lo que el script haga una vez arrancado ya no esta restringido al
    workspace; el sandbox cubre que se ejecute, no lo que ejecuta. Si eso llega
    a importar, el siguiente paso es lanzarlo en un contenedor o con un usuario
    limitado, no mas comprobaciones aqui.

    Args:
        script: Ruta relativa al workspace del script a ejecutar.
        args: Argumentos de linea de comandos para el script. Opcional.

    Returns:
        "[exit N]" seguido de la salida combinada (stdout + stderr), truncada a
        _MAX_OUTPUT caracteres; o "Error: ..." si la ruta se sale del sandbox,
        el script no existe, su extension no esta permitida o supero el timeout.
    """
    try:
        target = _resolve(script)
    except ValueError as e:
        return f"Error: {e}"

    interpreter = _INTERPRETERS.get(target.suffix.lower())
    if interpreter is None:
        permitidas = ", ".join(_INTERPRETERS)
        return f"Error: tipo de script no permitido: '{script}' (permitidos: {permitidas})"
    if not target.is_file():
        return f"Error: el script no existe: {script}"

    args = args or []
    if not all(isinstance(a, str) for a in args):
        return "Error: 'args' debe ser una lista de strings"

    try:
        completed = subprocess.run(
            [*interpreter, str(target), *args],
            cwd=target.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SCRIPT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Error: el script supero el timeout de {SCRIPT_TIMEOUT}s"
    except OSError as e:
        return f"Error al ejecutar el script: {e}"

    output = f"{completed.stdout}{completed.stderr}".strip() or "(sin salida)"
    if len(output) > _MAX_OUTPUT:
        output = f"{output[:_MAX_OUTPUT]}\n... (salida truncada a {_MAX_OUTPUT} caracteres)"
    return f"[exit {completed.returncode}]\n{output}"

SHELL_TOOLS = [
    ToolSpec(
        name="run_script",
        description="Ejecuta un script Python (.py) que ya existe dentro del workspace y devuelve su salida y codigo de salida. No sirve para comandos del sistema.",
        parameters={
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "Ruta relativa al workspace del script .py a ejecutar.",
                },
                "args": {
                    "type": "array",
                    "description": "Argumentos de linea de comandos para el script (lista de strings).",
                },
            },
            "required": ["script"],
        },
        handler=run_script,
        permission=Permission.EXECUTE,
        timeout_seconds=SCRIPT_TIMEOUT + 5,
    ),
]
