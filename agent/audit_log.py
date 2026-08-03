"""Registro (audit log) de cada llamada a tool, en JSON Lines."""
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.config import TOOL_LOG_FILE

# Numero maximo de caracteres del resultado que se guarda en el log, para no
# disparar el tamano del archivo con resultados largos (p. ej. read_file).
_RESULT_PREVIEW_LIMIT = 500


def log_tool_call(
    *,
    name: str,
    args: dict | None,
    permission: str | None,
    duration_seconds: float,
    status: str,
    result: str,
    log_file: Path = TOOL_LOG_FILE,
) -> None:
    """Anade una linea al registro de llamadas a tools.

    Se llama exactamente una vez por cada invocacion de execute_tool() (ver
    agent/tools/executor.py), tanto si la tool se ejecuto con exito como si
    se rechazo o fallo, para tener trazabilidad completa de que se pidio, con
    que argumentos y que resultado.

    Args:
        name: Nombre de la tool solicitada (puede no existir en la allowlist).
        args: Argumentos ya parseados de la llamada, o None si no llego a
            parsearse el JSON (p. ej. tool desconocida).
        permission: Valor de Permission de la tool como string, o None si la
            tool no existe en la allowlist.
        duration_seconds: Segundos que tardo la comprobacion/ejecucion completa.
        status: Uno de "ok", "rejected_unknown", "rejected_permission",
            "rejected_invalid_args", "timeout" o "error".
        result: Texto del resultado (o del error) devuelto al modelo; se
            trunca a _RESULT_PREVIEW_LIMIT caracteres al guardarlo.
        log_file: Archivo donde anadir la linea. Por defecto
            agent.config.TOOL_LOG_FILE; parametrizable para poder probar esta
            funcion sin escribir en el log real (ver autochequeo mas abajo).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": name,
        "args": args,
        "permission": permission,
        "duration_s": round(duration_seconds, 4),
        "status": status,
        "result_preview": result[:_RESULT_PREVIEW_LIMIT],
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        _test_log = Path(tmp) / "test_tool_calls.log"
        log_tool_call(
            name="_autocheck",
            args={"x": 1},
            permission="read",
            duration_seconds=0.001,
            status="ok",
            result="resultado de prueba",
            log_file=_test_log,
        )
        _lines = _test_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(_lines) == 1
        _parsed = json.loads(_lines[0])
        assert _parsed["tool"] == "_autocheck"
        assert _parsed["status"] == "ok"
        assert _parsed["args"] == {"x": 1}

    print("OK: agent/audit_log.py autochequeo pasado")
