"""Tool de archivos restringida a WORKSPACE_DIR (sandbox)."""
from pathlib import Path

from agent.config import WORKSPACE_DIR


def _resolve(path: str) -> Path:
    resolved = (WORKSPACE_DIR / path).resolve()
    if not resolved.is_relative_to(WORKSPACE_DIR.resolve()):
        raise ValueError(f"ruta fuera del sandbox: {path}")
    return resolved


def list_files(path: str = ".") -> str:
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

TOOL_DISPATCH = {
    "list_files": list_files,
    "read_file": read_file,
}


if __name__ == "__main__":
    assert "Error" not in list_files("."), "listar el workspace no deberia fallar"
    assert "fuera del sandbox" in list_files("../"), "escapar con ../ deberia fallar"
    assert "fuera del sandbox" in read_file("../config.py"), "leer fuera del sandbox deberia fallar"
    print("OK: agent/tools/files.py autochequeo pasado")
