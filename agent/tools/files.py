"""Tool de archivos restringida a WORKSPACE_DIR (sandbox)."""
from pathlib import Path

from agent.config import WORKSPACE_DIR


def _resolve(path: str) -> Path:
    """Resuelve una ruta relativa contra WORKSPACE_DIR y valida que no se escape del sandbox.

    Args:
        path: Ruta relativa (puede incluir "..") introducida por el modelo.

    Returns:
        Ruta absoluta resuelta, garantizada dentro de WORKSPACE_DIR.

    Raises:
        ValueError: Si la ruta resuelta cae fuera de WORKSPACE_DIR.
    """
    resolved = (WORKSPACE_DIR / path).resolve()
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


# Descripcion de las tools en formato OpenAI, para pasarla a
# client.chat.completions.create(tools=TOOL_SCHEMAS) y que el modelo sepa
# que puede invocarlas y con que argumentos.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lista los archivos y carpetas de un directorio dentro del workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta relativa al workspace (por defecto '.').",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee el contenido de un archivo de texto dentro del workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta relativa al workspace del archivo a leer.",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

# Mapeo nombre de tool -> funcion Python real, para que agent/loop.py pueda
# ejecutar la tool que pida el modelo sin conocer los detalles de cada una.
TOOL_DISPATCH = {
    "list_files": list_files,
    "read_file": read_file,
}


if __name__ == "__main__":
    assert "Error" not in list_files("."), "listar el workspace no deberia fallar"
    assert "fuera del sandbox" in list_files("../"), "escapar con ../ deberia fallar"
    assert "fuera del sandbox" in read_file("../config.py"), "leer fuera del sandbox deberia fallar"
    print("OK: agent/tools/files.py autochequeo pasado")
