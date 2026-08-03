"""Tool de archivos restringida a WORKSPACE_DIR (sandbox)."""
from pathlib import Path

from agent.config import WORKSPACE_DIR
from agent.tools.spec import Permission, ToolSpec


def _resolve(path: str) -> Path:
    """Resuelve una ruta relativa contra WORKSPACE_DIR y valida que no se escape del sandbox.

    Algunos modelos (sobre todo los mas pequenos, p. ej. qwen2.5:1.5b) no
    siguen al pie de la letra la instruccion de usar una ruta relativa y
    devuelven algo como "/workspace" o "/workspace/archivo.txt", asumiendo
    una convencion tipo Docker donde "/workspace" es la raiz montada. Sin
    normalizar, pathlib trata ese "/" inicial como absoluto y descarta
    WORKSPACE_DIR al hacer el join, lo que tira la ruta fuera del sandbox
    aunque la intencion del modelo fuera valida. Por eso se reconoce ese
    prefijo especifico (el nombre real de la carpeta sandbox) y se recorta
    antes de resolver; cualquier otra ruta absoluta se trata igual que antes.

    Args:
        path: Ruta relativa (puede incluir "..") introducida por el modelo.

    Returns:
        Ruta absoluta resuelta, garantizada dentro de WORKSPACE_DIR.

    Raises:
        ValueError: Si la ruta resuelta cae fuera de WORKSPACE_DIR.
    """
    normalized = path.replace("\\", "/")
    sandbox_prefix = "/" + WORKSPACE_DIR.name
    if normalized == sandbox_prefix or normalized.startswith(sandbox_prefix + "/"):
        normalized = normalized[len(sandbox_prefix):].lstrip("/") or "."

    resolved = (WORKSPACE_DIR / normalized).resolve()
    if not resolved.is_relative_to(WORKSPACE_DIR.resolve()):
        raise ValueError(f"ruta fuera del sandbox: {path}")
    return resolved


def list_files(path: str = ".") -> str:
    """Lista los nombres de archivos y carpetas de un directorio dentro del workspace.

    Los errores (ruta fuera del sandbox, ruta inexistente, no es un
    directorio) se devuelven como texto en vez de lanzar una excepcion, para
    que el propio modelo los vea en el resultado de la tool y pueda reintentar.

    Args:
        path: Ruta relativa al workspace a listar. Por defecto ".".

    Returns:
        Un nombre por linea (carpetas con "/" al final), "(vacio)" si el
        directorio no tiene contenido, o un mensaje "Error: ..." si algo falla.
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"Error: {e}"

    if not target.exists():
        return f"Error: la ruta no existe: {path}"
    if not target.is_dir():
        return f"Error: no es un directorio: {path}"

    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
    return "\n".join(entries) if entries else "(vacio)"


def read_file(path: str) -> str:
    """Lee el contenido completo de un archivo de texto dentro del workspace.

    Igual que list_files, los errores se devuelven como texto (no como
    excepcion) para que el modelo pueda verlos y ajustar su siguiente llamada.

    Args:
        path: Ruta relativa al workspace del archivo a leer.

    Returns:
        Contenido del archivo como texto (UTF-8, con reemplazo de caracteres
        invalidos), o un mensaje "Error: ..." si la ruta no es valida, no
        existe, no es un archivo, o falla la lectura.
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"Error: {e}"

    if not target.exists():
        return f"Error: el archivo no existe: {path}"
    if not target.is_file():
        return f"Error: no es un archivo: {path}"

    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Error al leer el archivo: {e}"


# Tools de este modulo como ToolSpec (ver agent/tools/spec.py).
# agent/tools/registry.py las agrega en ALL_TOOLS, la allowlist explicita de
# tools que el agente puede ejecutar.
FILES_TOOLS = [
    ToolSpec(
        name="list_files",
        description="Lista los archivos y carpetas de un directorio dentro del workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa al workspace (por defecto '.').",
                }
            },
        },
        handler=list_files,
        permission=Permission.READ,
    ),
    ToolSpec(
        name="read_file",
        description="Lee el contenido de un archivo de texto dentro del workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa al workspace del archivo a leer.",
                }
            },
            "required": ["path"],
        },
        handler=read_file,
        permission=Permission.READ,
    ),
]


if __name__ == "__main__":
    assert "Error" not in list_files("."), "listar el workspace no deberia fallar"
    assert "fuera del sandbox" in list_files("../"), "escapar con ../ deberia fallar"
    assert "fuera del sandbox" in read_file("../config.py"), "leer fuera del sandbox deberia fallar"
    assert {t.name for t in FILES_TOOLS} == {"list_files", "read_file"}

    # Algunos modelos (p. ej. qwen2.5:1.5b) devuelven "/workspace" en vez de
    # "." como path, asumiendo una convencion tipo Docker donde "/workspace"
    # es la raiz del sandbox. Sin normalizar, pathlib trata ese "/" inicial
    # como absoluto y descarta WORKSPACE_DIR, tirando la ruta fuera del
    # sandbox (ver logs/tool_calls.log linea del 2026-08-03T18:30:29).
    assert "Error" not in list_files("/workspace"), "'/workspace' deberia equivaler a la raiz del sandbox"
    assert "Error" not in read_file("/workspace/prueba.txt"), "'/workspace/archivo' deberia resolverse dentro del sandbox"
    # Absolutas de verdad (fuera del nombre del sandbox) siguen bloqueadas.
    assert "fuera del sandbox" in list_files("/etc"), "una ruta absoluta ajena al sandbox debe seguir rechazada"

    print("OK: agent/tools/files.py autochequeo pasado")
