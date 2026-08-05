"""Tests de la tool de búsqueda semántica (agent/tools/semantic.py)."""
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
