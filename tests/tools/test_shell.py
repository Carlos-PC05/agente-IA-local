"""Tests de agent/tools/shell.py: ejecucion de scripts, allowlist, sandbox y timeout."""
import pytest

from agent.tools import shell as shell_mod
from agent.tools.shell import SHELL_TOOLS, run_script
from agent.tools.spec import Permission


@pytest.fixture
def script(workspace):
    """Devuelve una funcion que escribe un script .py en el workspace del test."""

    def _write(name: str, code: str) -> str:
        (workspace / name).write_text(code, encoding="utf-8")
        return name

    return _write


def test_ejecuta_y_devuelve_salida_y_codigo(script):
    salida = run_script(script("ok.py", "print('hola')"))
    assert salida == "[exit 0]\nhola"


def test_captura_stderr_y_codigo_de_error(script):
    salida = run_script(script("falla.py", "import sys; sys.exit('roto')"))
    assert salida.startswith("[exit 1]")
    assert "roto" in salida


def test_pasa_argumentos_al_script(script):
    code = "import sys; print(' '.join(sys.argv[1:]))"
    assert run_script(script("args.py", code), ["uno", "dos"]) == "[exit 0]\nuno dos"


def test_rechaza_args_que_no_sean_strings(script):
    assert "lista de strings" in run_script(script("args.py", "print(1)"), [1, 2])


def test_rechaza_extension_fuera_de_la_allowlist(workspace):
    (workspace / "hack.sh").write_text("echo hola", encoding="utf-8")
    assert "tipo de script no permitido" in run_script("hack.sh")


def test_rechaza_scripts_fuera_del_sandbox(workspace):
    (workspace.parent / "fuera.py").write_text("print('fuera')", encoding="utf-8")
    assert "fuera del sandbox" in run_script("../fuera.py")


def test_script_inexistente(workspace):
    assert "no existe" in run_script("fantasma.py")


def test_timeout_mata_el_script(script, monkeypatch):
    monkeypatch.setattr(shell_mod, "SCRIPT_TIMEOUT", 0.5)
    salida = run_script(script("lento.py", "import time; time.sleep(30)"))
    assert "supero el timeout" in salida


def test_trunca_salidas_largas(script):
    salida = run_script(script("hablador.py", "print('x' * 5000)"))
    assert "salida truncada" in salida
    assert len(salida) < 5000


def test_tool_declarada_con_permiso_execute():
    (tool,) = SHELL_TOOLS
    assert tool.name == "run_script"
    assert tool.permission == Permission.EXECUTE
    # El timeout de la tool debe ser mayor que el del subproceso, para que
    # salte antes el que si mata al proceso hijo.
    assert tool.timeout_seconds > shell_mod.SCRIPT_TIMEOUT
