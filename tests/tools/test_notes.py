"""Tests de agent/tools/notes.py: ciclo de vida de una nota y saneado del titulo."""
from agent.tools.notes import (
    NOTES_TOOLS,
    _sanitize_title,
    append_note,
    create_note,
    delete_note,
    list_notes,
    read_note,
)


def test_ciclo_completo_de_una_nota(notes_dir):
    assert list_notes() == "(sin notas)"

    assert "Error" not in create_note("Comprar leche", "No quedan huevos")
    assert read_note("Comprar leche") == "No quedan huevos"
    assert list_notes() == "comprar-leche"

    assert "Error" not in append_note("Comprar leche", "Y pan")
    assert read_note("comprar-leche") == "No quedan huevos\n\nY pan"

    assert "Error" not in delete_note("comprar leche")
    assert list_notes() == "(sin notas)"


def test_create_sobrescribe_y_append_crea(notes_dir):
    create_note("A", "primera version")
    create_note("A", "version 2")
    assert read_note("a") == "version 2"

    assert "Error" not in append_note("B", "solo esta")
    assert read_note("b") == "solo esta"


def test_titulos_equivalentes_apuntan_a_la_misma_nota(notes_dir):
    create_note("  HOLA mundo !! ", "contenido")
    assert read_note("hola-mundo") == "contenido"
    assert _sanitize_title("  HOLA mundo  !! ") == "hola-mundo"
    assert _sanitize_title("!!!") == "sin-titulo"


def test_titulo_no_puede_escapar_del_directorio_de_notas(notes_dir):
    (notes_dir.parent / "config.md").write_text("fuera", encoding="utf-8")

    # La sanitizacion convierte ".." y "/" en guiones, asi que la nota
    # apuntada simplemente no existe dentro de NOTES_DIR.
    assert _sanitize_title("../../config.py") == "config-py"
    assert "no existe" in read_note("../config")
    assert "no existe" in read_note("/etc/passwd")


def test_errores_sobre_notas_inexistentes(notes_dir):
    assert "no existe" in read_note("fantasma")
    assert "no existe" in delete_note("fantasma")


def test_tools_declaradas():
    assert {t.name for t in NOTES_TOOLS} == {
        "create_note",
        "append_note",
        "list_notes",
        "read_note",
        "delete_note",
    }
