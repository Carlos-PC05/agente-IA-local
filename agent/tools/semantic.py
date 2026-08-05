"""Tool de busqueda semantica sobre los documentos del workspace.

Usa embeddings de Ollama (EMBEDDING_MODEL) para indexar el contenido de
WORKSPACE_DIR en un archivo JSON (INDEX_FILE) y buscar en el por similitud
de coseno. El indice se construye manualmente con
`python -m agent.tools.semantic --reindex`; la tool search_documents solo
lee el indice y embedia la consulta del modelo.
"""
from agent.config import CHUNK_MAX_CHARS


def _chunk_text(text: str) -> list[str]:
    """Divide un texto en fragmentos de como mucho CHUNK_MAX_CHARS caracteres.

    Los parrafos (separados por linea en blanco) se agrupan mientras quepan
    en el limite; un parrafo que lo supere se corta en trozos del tamano
    exacto del limite. Los parrafos vacios se ignoran.

    Args:
        text: Texto completo de un documento.

    Returns:
        Fragmentos listos para embedir, sin espacios sobrantes.
    """
    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current) + len(paragraph) <= CHUNK_MAX_CHARS:
            current = f"{current}\n\n{paragraph}" if current else paragraph
        else:
            if current:
                chunks.append(current)
                current = ""
            while len(paragraph) > CHUNK_MAX_CHARS:
                chunks.append(paragraph[:CHUNK_MAX_CHARS])
                paragraph = paragraph[CHUNK_MAX_CHARS:]
            current = paragraph

    if current:
        chunks.append(current)
    return chunks
