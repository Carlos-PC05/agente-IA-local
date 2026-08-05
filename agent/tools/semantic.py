"""Tool de busqueda semantica sobre los documentos del workspace.

Usa embeddings de Ollama (EMBEDDING_MODEL) para indexar el contenido de
WORKSPACE_DIR en un archivo JSON (INDEX_FILE) y buscar en el por similitud
de coseno. El indice se construye manualmente con
`python -m agent.tools.semantic --reindex`; la tool search_documents solo
lee el indice y embedia la consulta del modelo.
"""
import json
import os
import sys
from pathlib import Path

import openai

from agent.config import (
    CHUNK_MAX_CHARS,
    DEFAULT_TOP_K,
    EMBEDDING_MODEL,
    INDEX_FILE,
    OLLAMA_BASE_URL,
    SEARCH_EXTENSIONS,
    WORKSPACE_DIR,
)

# Tamano de lote al embedir: se piden los vectores de 64 fragmentos por
# llamada para no saturar a Ollama con peticiones minisculas.
_EMBED_BATCH = 64

# Tamano maximo (en caracteres) del fragmento mostrado en los resultados.
_SNIPPET_MAX_CHARS = 200


def _new_client() -> openai.OpenAI:
    """Cliente OpenAI apuntando a Ollama, igual que en main.py."""
    return openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def _embed_texts(texts: list[str], client) -> list[list[float]]:
    """Embedia una lista de textos con el modelo de Ollama configurado.

    Los vectores se piden en lotes de _EMBED_BATCH y se devuelven en el
    mismo orden de entrada. Los errores de la API no se capturan aqui: los
    convierten en "Error: ..." los llamadores publicos (reindex, search).

    Args:
        texts: Textos a embedir (fragmentos del indice o la consulta).
        client: Cliente `openai.OpenAI` apuntando a Ollama.

    Returns:
        Lista con un vector por texto, en el orden de `texts`.
    """
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        batch = texts[start : start + _EMBED_BATCH]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors


def _collect_files() -> list[Path]:
    """Lista los archivos indexables del workspace, recursivo y ordenado.

    Solo entran archivos cuya extension esta en SEARCH_EXTENSIONS (texto
    plano legible con read_text); los binarios (p. ej. .png) se ignoran.

    Returns:
        Rutas absolutas de los archivos a indexar, ordenadas.
    """
    return sorted(
        path
        for path in WORKSPACE_DIR.rglob("*")
        if path.is_file() and path.suffix in SEARCH_EXTENSIONS
    )


def reindex() -> str:
    """Reconstruye el indice semantico embebiendo todo el workspace.

    Recorre WORKSPACE_DIR, trocea cada archivo, embedie los fragmentos con
    EMBEDDING_MODEL y escribe INDEX_FILE con escritura atomica (archivo
    temporal + os.replace) para que una interrupcion no deje el indice a
    medias. Un archivo ilegible se salta avisando por stderr.

    Returns:
        "Indexados <N> fragmentos de <M> archivos", o "Error: ..." si algo
        fallo (nunca lanza).
    """
    files = _collect_files()
    if not files:
        return "Error: no hay documentos indexables en el workspace"

    client = _new_client()
    chunks: list[dict] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[aviso] no se pudo leer {path}: {e}", file=sys.stderr)
            continue
        for fragment in _chunk_text(text):
            chunks.append({"file": path.relative_to(WORKSPACE_DIR.parent).as_posix(), "text": fragment})

    if not chunks:
        return "Error: no se pudo indexar ningun fragmento"

    try:
        vectors = _embed_texts([c["text"] for c in chunks], client)
    except Exception as e:
        return f"Error al generar embeddings: {e}"

    for chunk, vector in zip(chunks, vectors):
        chunk["vector"] = vector

    index = {"model": EMBEDDING_MODEL, "files": len(files), "chunks": chunks}
    try:
        tmp = INDEX_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, INDEX_FILE)
    except OSError as e:
        return f"Error al guardar el indice: {e}"

    return f"Indexados {len(chunks)} fragmentos de {len(files)} archivos"


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
        if len(current) + len(paragraph) + (2 if current else 0) <= CHUNK_MAX_CHARS:
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
