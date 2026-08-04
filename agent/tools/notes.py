"""Tool de notas persistentes: crear, anadir, listar, leer y borrar notas en disco."""
import re
from pathlib import Path

from agent.config import NOTES_DIR
from agent.tools.spec import Permission, ToolSpec

# Caracteres que se quedan tal cual en el nombre de archivo de una nota.
_SAFE_CHARS = re.compile(r"[^a-z0-9]+")


def _sanitize_title(title: str) -> str:
    """Convierte un titulo de nota en un nombre de archivo seguro.

    Los modelos no siempre devuelven titulos limpios, asi que el nombre de la
    nota se deriva del titulo en vez de fiar el nombre completo al modelo:
    minusculas, cualquier caracter no alfanumerico pasa a ser un guion, y se
    recortan los guiones del inicio y del final. Si el resultado queda vacio
    se usa "sin-titulo" para tener siempre un nombre utilizable.

    Args:
        title: Titulo de la nota tal y como lo da el modelo.

    Returns:
        Nombre de archivo (sin extension) seguro para usar en disco.
    """
    slug = _SAFE_CHARS.sub("-", title.lower()).strip("-") or "sin-titulo"
    return slug


def _resolve(title: str) -> Path:
    """Resuelve un titulo de nota a la ruta de su archivo .md dentro de NOTES_DIR.

    Mismo patron de sandbox que agent/tools/files.py:_resolve: se parte de
    NOTES_DIR, se anade el titulo sanitizado y se comprueba que la ruta
    resultante no se sale del directorio de notas (is_relative_to). Aunque
    el titulo ya se sanea, la comprobacion cubre cualquier ruta absoluta o
    con ".." que un modelo raro pueda colar.

    Args:
        title: Titulo de la nota (o nombre de archivo) referido por el modelo.

    Returns:
        Ruta absoluta dentro de NOTES_DIR, garantizada.
    """
    normalized = title.replace("\\", "/").strip("/")
    resolved = (NOTES_DIR / _sanitize_title(normalized)).with_suffix(".md").resolve()
    if not resolved.is_relative_to(NOTES_DIR.resolve()):
        raise ValueError(f"nota fuera del directorio de notas: {title}")
    return resolved


def create_note(title: str, content: str) -> str:
    """Crea una nota (o sobrescribe su contenido si ya existe).

    Args:
        title: Titulo de la nota; de el se deriva el nombre del archivo.
        content: Texto completo de la nota.

    Returns:
        Un mensaje de confirmacion, o "Error: ..." si algo fallo.
    """
    try:
        path = _resolve(title)
    except ValueError as e:
        return f"Error: {e}"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"Error al guardar la nota: {e}"

    return f"Nota '{title}' creada"


def append_note(title: str, content: str) -> str:
    """Anade contenido al final de una nota, creandola si no existe.

    Cada anadido se separa del contenido previo con una linea en blanco, para
    que las notas que crecen por partes se lean bien como texto plano.

    Args:
        title: Titulo de la nota sobre la que anadir.
        content: Texto a anadir al final de la nota.

    Returns:
        Un mensaje de confirmacion, o "Error: ..." si algo fallo.
    """
    try:
        path = _resolve(title)
    except ValueError as e:
        return f"Error: {e}"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        previous = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        new_content = f"{previous}\n\n{content}" if previous else content
        path.write_text(new_content, encoding="utf-8")
    except OSError as e:
        return f"Error al guardar la nota: {e}"

    return f"Nota '{title}' actualizada"


def list_notes() -> str:
    """Lista los titulos de todas las notas guardadas.

    Returns:
        Un titulo por linea (sin la extension .md), o "(sin notas)" si el
        directorio de notas esta vacio.
    """
    if not NOTES_DIR.exists():
        return "(sin notas)"

    notes = sorted(path for path in NOTES_DIR.iterdir() if path.is_file() and path.suffix == ".md")
    return "\n".join(path.stem for path in notes) if notes else "(sin notas)"


def read_note(title: str) -> str:
    """Lee el contenido completo de una nota.

    Args:
        title: Titulo de la nota a leer.

    Returns:
        Contenido de la nota como texto, o "Error: ..." si la nota no existe
        o su archivo no es legible.
    """
    try:
        path = _resolve(title)
    except ValueError as e:
        return f"Error: {e}"

    if not path.exists():
        return f"Error: la nota no existe: {title}"
    if not path.is_file():
        return f"Error: '{title}' no es un archivo"

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Error al leer la nota: {e}"


def delete_note(title: str) -> str:
    """Borra una nota existente.

    Args:
        title: Titulo de la nota a borrar.

    Returns:
        Un mensaje de confirmacion, o "Error: ..." si la nota no existe.
    """
    try:
        path = _resolve(title)
    except ValueError as e:
        return f"Error: {e}"

    if not path.exists():
        return f"Error: la nota no existe: {title}"

    try:
        path.unlink()
    except OSError as e:
        return f"Error al borrar la nota: {e}"

    return f"Nota '{title}' borrada"


# Tools de este modulo como ToolSpec (ver agent/tools/spec.py).
# agent/tools/registry.py las agrega en ALL_TOOLS, la allowlist explicita de
# tools que el agente puede ejecutar.
NOTES_TOOLS = [
    ToolSpec(
        name="create_note",
        description="Crea una nota persistente con el titulo y contenido dados. Si ya existe una nota con ese titulo, la sobrescribe.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo de la nota."},
                "content": {"type": "string", "description": "Contenido completo de la nota."},
            },
            "required": ["title", "content"],
        },
        handler=create_note,
        permission=Permission.WRITE,
    ),
    ToolSpec(
        name="append_note",
        description="Anade contenido al final de una nota existente; si la nota no existe, la crea.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo de la nota a ampliar."},
                "content": {"type": "string", "description": "Contenido a anadir al final de la nota."},
            },
            "required": ["title", "content"],
        },
        handler=append_note,
        permission=Permission.WRITE,
    ),
    ToolSpec(
        name="list_notes",
        description="Lista los titulos de todas las notas guardadas, uno por linea.",
        parameters={"type": "object", "properties": {}},
        handler=list_notes,
        permission=Permission.READ,
    ),
    ToolSpec(
        name="read_note",
        description="Lee el contenido completo de una nota por su titulo.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo de la nota a leer."},
            },
            "required": ["title"],
        },
        handler=read_note,
        permission=Permission.READ,
    ),
    ToolSpec(
        name="delete_note",
        description="Borra una nota existente por su titulo.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo de la nota a borrar."},
            },
            "required": ["title"],
        },
        handler=delete_note,
        permission=Permission.WRITE,
    ),
]
