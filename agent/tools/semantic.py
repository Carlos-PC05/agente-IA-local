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
from agent.tools.spec import Permission, ToolSpec

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


def _load_index() -> dict | None:
    """Lee el indice semantico de disco.

    Returns:
        El diccionario del indice, o None si el archivo no existe o su
        JSON es invalido (se considera que no hay indice).
    """
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud de coseno entre dos vectores, normalizados L2.

    Args:
        a: Primer vector.
        b: Segundo vector.

    Returns:
        Coseno en [-1.0, 1.0]; 0.0 si algun vector es todo ceros.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _snippet(text: str) -> str:
    """Compacta un fragmento para mostrarlo en una sola linea (max _SNIPPET_MAX_CHARS)."""
    one_line = " ".join(text.split())
    return one_line[:_SNIPPET_MAX_CHARS]


def search_documents(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Busca los fragmentos del indice mas similares a `query`.

    Carga el indice de disco, embedia la consulta y devuelve los top_k
    fragmentos con mayor similitud de coseno, de mayor a menor, con su
    archivo, la puntuacion (0-1) y un fragmento del texto.

    Args:
        query: Consulta en lenguaje natural del modelo.
        top_k: Numero de resultados (se recorta a [1, 10] y al numero de
            fragmentos del indice).

    Returns:
        Una linea por resultado como
        "workspace/a.md (0.82): 'texto del fragmento...'", o "Error: ..."
        si no hay indice o fallan los embeddings (nunca lanza).
    """
    query = query.strip()
    if not query:
        return "Error: la consulta no puede estar vacia"

    index = _load_index()
    if index is None:
        return "Error: no hay indice. Ejecuta `python -m agent.tools.semantic --reindex`"

    chunks = index.get("chunks", [])
    if not chunks:
        return "Error: el indice no tiene fragmentos. Ejecuta `python -m agent.tools.semantic --reindex`"

    try:
        query_vector = _embed_texts([query], _new_client())[0]
    except Exception as e:
        return f"Error: al generar embeddings: {e}"

    ranked = sorted(
        ((_cosine_similarity(query_vector, c["vector"]), c) for c in chunks),
        key=lambda item: item[0],
        reverse=True,
    )

    top_k = max(1, min(int(top_k), 10))
    lines = [
        f"{chunk['file']} ({score:.2f}): \"{_snippet(chunk['text'])}\""
        for score, chunk in ranked[:top_k]
    ]
    return "\n".join(lines)


# Tools de este modulo como ToolSpec (ver agent/tools/spec.py).
# agent/tools/registry.py las agrega en ALL_TOOLS, la allowlist explicita.
SEMANTIC_TOOLS = [
    ToolSpec(
        name="search_documents",
        description="Busca en los documentos del workspace por similitud semantica: devuelve los fragmentos mas relevantes con su archivo y una puntuacion de 0 a 1. Si no hay indice, ejecuta python -m agent.tools.semantic --reindex.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Consulta en lenguaje natural sobre el contenido de los documentos."},
                "top_k": {"type": "integer", "description": "Numero maximo de resultados (entre 1 y 10; por defecto 5)."},
            },
            "required": ["query"],
        },
        handler=search_documents,
        permission=Permission.READ,
        timeout_seconds=30.0,
    ),
]
