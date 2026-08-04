"""Tests de agent/tools/files.py: listado, lectura, movimiento y limites del sandbox."""
from agent.tools.files import FILES_TOOLS, list_files, move_file, read_file


def test_list_files_vacio_y_con_contenido(workspace):
    assert list_files(".") == "(vacio)"

    (workspace / "a.txt").write_text("hola", encoding="utf-8")
    (workspace / "sub").mkdir()
    assert list_files(".") == "a.txt\nsub/"


def test_read_file_lee_y_reporta_errores(workspace):
    (workspace / "a.txt").write_text("contenido", encoding="utf-8")
    assert read_file("a.txt") == "contenido"
    assert "no existe" in read_file("fantasma.txt")

    (workspace / "sub").mkdir()
    assert "no es un archivo" in read_file("sub")


def test_move_file_mueve_crea_carpetas_y_no_sobrescribe(workspace):
    (workspace / "a.txt").write_text("contenido", encoding="utf-8")

    assert "Error" not in move_file("a.txt", "sub/b.txt")
    assert (workspace / "sub" / "b.txt").read_text(encoding="utf-8") == "contenido"
    assert not (workspace / "a.txt").exists()

    # El destino ya existe: falla en vez de reemplazarlo.
    (workspace / "c.txt").write_text("otro", encoding="utf-8")
    assert "el destino ya existe" in move_file("c.txt", "sub/b.txt")
    assert (workspace / "sub" / "b.txt").read_text(encoding="utf-8") == "contenido"

    assert "no existe" in move_file("fantasma.txt", "d.txt")


def test_sandbox_bloquea_salidas(workspace):
    (workspace.parent / "secreto.txt").write_text("fuera", encoding="utf-8")

    assert "fuera del sandbox" in list_files("../")
    assert "fuera del sandbox" in read_file("../secreto.txt")
    assert "fuera del sandbox" in list_files("/etc")
    assert "fuera del sandbox" in move_file("../secreto.txt", "robado.txt")


def test_prefijo_workspace_se_normaliza(workspace):
    """Algunos modelos devuelven rutas tipo '/workspace/x.txt' (convencion Docker)."""
    (workspace / "a.txt").write_text("contenido", encoding="utf-8")

    assert list_files("/workspace") == "a.txt"
    assert read_file("/workspace/a.txt") == "contenido"


def test_tools_declaradas():
    assert {t.name for t in FILES_TOOLS} == {"list_files", "read_file", "move_file"}
