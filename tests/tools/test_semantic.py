"""Tests de la tool de búsqueda semántica (agent/tools/semantic.py)."""
import json
from pathlib import Path

import pytest

from agent.tools import semantic


def test_chunk_agrupa_parrafos_cortos():
    chunks = semantic._chunk_text("p1\n\np2\n\np3")
    assert chunks == ["p1\n\np2\n\np3"]


def test_chunk_separa_cuando_la_suma_excede_el_limite():
    p1 = "x" * 400
    p2 = "y" * 400
    chunks = semantic._chunk_text(f"{p1}\n\n{p2}")
    assert chunks == [p1, p2]


def test_chunk_corta_un_parrafo_gigante():
    parrafo = "a" * 1200
    chunks = semantic._chunk_text(parrafo)
    assert chunks == ["a" * 500, "a" * 500, "a" * 200]
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_ignora_parrafos_vacios():
    assert semantic._chunk_text("a\n\n\n\nb") == ["a\n\nb"]


def test_chunk_presupuesta_el_separador_en_el_limite():
    chunks = semantic._chunk_text("x" * 499 + "\n\n" + "y")
    assert chunks == ["x" * 499, "y"]
    assert all(len(c) <= semantic.CHUNK_MAX_CHARS for c in chunks)


class _FakeEmbedding:
    def __init__(self, vector):
        self.embedding = vector


class _FakeEmbedResponse:
    def __init__(self, vectors):
        self.data = [_FakeEmbedding(v) for v in vectors]


class _FakeEmbedClient:
    """Cliente falso: cada texto se embedia a [1.0, 0.0] si contiene 'gato'."""

    def __init__(self):
        self.calls = []
        self.embeddings = _FakeEmbeddings(self.calls)


class _FakeEmbeddings:
    """Replica de client.embeddings del SDK de OpenAI para el cliente falso."""

    def __init__(self, calls):
        self.calls = calls

    def create(self, model, input):
        self.calls.append(model)
        vectors = [[1.0, 0.0] if "gato" in t else [0.0, 1.0] for t in input]
        return _FakeEmbedResponse(vectors)


@pytest.fixture
def fake_embedder(monkeypatch):
    """Monkeypatchea semantic._embed_texts por uno determinista (sin Ollama)."""
    def _embed(texts, client):
        return [[1.0, 0.0] if "gato" in t else [0.0, 1.0] for t in texts]

    monkeypatch.setattr(semantic, "_embed_texts", _embed)
    return _embed


def test_embed_texts_devuelve_un_vector_por_texto_en_orden():
    client = _FakeEmbedClient()
    vectors = semantic._embed_texts(["el gato duerme", "llueve afuera"], client)
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert client.calls == [semantic.EMBEDDING_MODEL], "debe usar el modelo de config"


def test_collect_files_filtra_por_extension(workspace):
    (workspace / "a.md").write_text("x", encoding="utf-8")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "b.py").write_text("x", encoding="utf-8")
    (workspace / "c.png").write_text("x", encoding="utf-8")
    files = semantic._collect_files()
    assert files == sorted([workspace / "a.md", workspace / "sub" / "b.py"])


def test_reindex_escribe_el_indice(workspace, semantic_index, fake_embedder):
    (workspace / "a.md").write_text("el gato duerme\n\nel perro ladra", encoding="utf-8")
    (workspace / "b.txt").write_text("llueve afuera", encoding="utf-8")
    (workspace / "c.png").write_text("no indexar", encoding="utf-8")

    result = semantic.reindex()

    assert result == "Indexados 2 fragmentos de 2 archivos"  # CORRECCION C1
    index = json.loads(semantic_index.read_text(encoding="utf-8"))
    assert index["model"] == "nomic-embed-text"
    assert index["files"] == 2
    assert len(index["chunks"]) == 2  # CORRECCION C1
    first = index["chunks"][0]
    assert first["file"] == "workspace/a.md"
    assert first["vector"] == [1.0, 0.0]
    assert index["chunks"][1]["file"] == "workspace/b.txt"  # CORRECCION C1
    assert index["chunks"][1]["vector"] == [0.0, 1.0]  # CORRECCION C1


def test_reindex_sin_documentos_devuelve_error(workspace, semantic_index, fake_embedder):
    result = semantic.reindex()
    assert result.startswith("Error:")


def test_reindex_sobrescribe_el_indice_anterior(workspace, semantic_index, fake_embedder):
    (workspace / "a.md").write_text("el gato", encoding="utf-8")
    semantic.reindex()
    (workspace / "a.md").write_text("el gato duerme", encoding="utf-8")
    semantic.reindex()
    index = json.loads(semantic_index.read_text(encoding="utf-8"))
    assert len(index["chunks"]) == 1
    assert index["chunks"][0]["text"] == "el gato duerme"
