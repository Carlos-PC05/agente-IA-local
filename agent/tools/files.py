"""Tool de archivos restringida a WORKSPACE_DIR (sandbox)."""
from pathlib import Path

from agent.config import WORKSPACE_DIR
from agent.tools.spec import Permission, ToolSpec


def _resolve(path: str) -> Path:
    """Resuelve una ruta relativa contra WORKSPACE_DIR y valida que no se escape del sandbox.

    Algunos modelos pequenos (p. ej. qwen2.5:1.5b) devuelven rutas tipo
    "/workspace/archivo.txt" asumiendo una convencion Docker. Sin normalizar,
    pathlib trataria ese "/" como absoluto y descartaria WORKSPACE_DIR al
    resolver, sacando la ruta del sandbox. Por eso ese prefijo se recorta
    antes de resolver; cualquier otra ruta absoluta se sigue rechazando.

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

    Los errores se devuelven como texto ("Error: ...") en vez de lanzar una
    excepcion, para que el modelo los vea en el resultado de la tool y reintente.

    Args:
        path: Ruta relativa al workspace a listar. Por defecto ".".

    Returns:
        Un nombre por linea (carpetas con "/" al final), o "(vacio)" si el
        directorio no tiene contenido.
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

    Igual que list_files, los errores se devuelven como texto ("Error: ...")
    en vez de lanzar una excepcion.

    Args:
        path: Ruta relativa al workspace del archivo a leer.

    Returns:
        Contenido del archivo como texto (UTF-8, con reemplazo de caracteres
        invalidos).
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


def move_file(source: str, destination: str) -> str:
    """Mueve o renombra un archivo dentro del workspace.

    Crea las carpetas intermedias del destino si no existen. No sobrescribe:
    si el destino ya existe, falla en vez de reemplazarlo. Igual que
    list_files y read_file, los errores se devuelven como texto en vez de
    lanzar una excepcion.

    Args:
        source: Ruta relativa al workspace del archivo a mover.
        destination: Ruta relativa al workspace del destino. Un nombre de
            archivo distinto en la misma carpeta equivale a renombrar.

    Returns:
        Un mensaje de confirmacion, o "Error: ..." si algo fallo.
    """
    try:
        source_path = _resolve(source)
        dest_path = _resolve(destination)
    except ValueError as e:
        return f"Error: {e}"

    if not source_path.exists():
        return f"Error: el archivo de origen no existe: {source}"
    if not source_path.is_file():
        return f"Error: no es un archivo: {source}"
    if dest_path.exists():
        return f"Error: el destino ya existe: {destination}"

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(dest_path)
    except OSError as e:
        return f"Error al mover el archivo: {e}"

    return f"Movido: {source} -> {destination}"


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
    ToolSpec(
        name="move_file",
        description="Mueve o renombra un archivo dentro del workspace. Crea las carpetas intermedias del destino si hacen falta; falla si el destino ya existe.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Ruta relativa al workspace del archivo a mover.",
                },
                "destination": {
                    "type": "string",
                    "description": "Ruta relativa al workspace del destino (nuevo nombre y/o carpeta).",
                },
            },
            "required": ["source", "destination"],
        },
        handler=move_file,
        permission=Permission.WRITE,
    ),
]


if __name__ == "__main__":
    assert "Error" not in list_files("."), "listar el workspace no deberia fallar"
    assert "fuera del sandbox" in list_files("../"), "escapar con ../ deberia fallar"
    assert "fuera del sandbox" in read_file("../config.py"), "leer fuera del sandbox deberia fallar"
    assert {t.name for t in FILES_TOOLS} == {"list_files", "read_file", "move_file"}

    # Caso real: algunos modelos devuelven "/workspace" en vez de "." (ver _resolve).
    assert "Error" not in list_files("/workspace"), "'/workspace' deberia equivaler a la raiz del sandbox"
    assert "Error" not in read_file("/workspace/prueba.txt"), "'/workspace/archivo' deberia resolverse dentro del sandbox"
    # Absolutas de verdad (fuera del nombre del sandbox) siguen bloqueadas.
    assert "fuera del sandbox" in list_files("/etc"), "una ruta absoluta ajena al sandbox debe seguir rechazada"

    print("OK: agent/tools/files.py autochequeo pasado")
