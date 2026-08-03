"""Punto unico de ejecucion de tools: allowlist + permiso + validacion + timeout + log."""
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from agent.audit_log import log_tool_call
from agent.config import ALLOWED_PERMISSION_LEVELS
from agent.tools import registry
from agent.tools.validation import ToolValidationError, validate_args

# Pool compartido para correr los handlers de las tools con un timeout.
# max_workers > 1 para que una tool colgada (ver limitacion mas abajo) no
# bloquee las siguientes llamadas: el pool sigue teniendo hilos libres aunque
# uno se quede atascado.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool")


def execute_tool(name: str, raw_arguments: str) -> str:
    """Ejecuta una tool pedida por el modelo, aplicando toda la capa de seguridad.

    Orden de comprobaciones (ver
    docs/superpowers/specs/2026-08-03-fase2-seguridad-tools-design.md):
    1. La tool debe estar registrada en agent/tools/registry.py (allowlist).
    2. Su Permission debe estar en agent.config.ALLOWED_PERMISSION_LEVELS.
    3. Sus argumentos deben parsear como JSON y validar contra su JSON Schema.
    4. Se ejecuta con un timeout (tool.timeout_seconds); un handler colgado
       mas alla del timeout deja de esperarse, pero el hilo sigue vivo en
       segundo plano (los hilos de Python no se pueden matar a la fuerza;
       limitacion conocida y documentada, relevante sobre todo para la
       futura tool de shell en Fase 3).

    En todos los casos (exito, rechazo o error) se registra la llamada con
    agent.audit_log.log_tool_call() antes de devolver el resultado. La
    funcion nunca lanza excepciones: cualquier fallo se convierte en un
    string "Error: ..." para que el modelo lo vea en el resultado de la tool.

    Args:
        name: Nombre de la tool tal y como la pide el modelo.
        raw_arguments: Argumentos de la tool-call como string JSON (tal cual
            los entrega la API de OpenAI en `call.function.arguments`).

    Returns:
        El resultado de la tool como texto, o un mensaje "Error: ..." si se
        rechazo por allowlist/permiso/validacion, si supero el timeout, o si
        el handler lanzo una excepcion.
    """
    start = time.perf_counter()
    tool = registry.get(name)

    if tool is None:
        result = f"Error: tool desconocida '{name}' (no esta en la allowlist)"
        log_tool_call(
            name=name,
            args=None,
            permission=None,
            duration_seconds=time.perf_counter() - start,
            status="rejected_unknown",
            result=result,
        )
        return result

    if tool.permission not in ALLOWED_PERMISSION_LEVELS:
        result = f"Error: la tool '{name}' requiere el permiso '{tool.permission.value}', no habilitado"
        log_tool_call(
            name=name,
            args=None,
            permission=tool.permission.value,
            duration_seconds=time.perf_counter() - start,
            status="rejected_permission",
            result=result,
        )
        return result

    args = None
    try:
        args = json.loads(raw_arguments or "{}")
        validate_args(tool.parameters, args)
    except (json.JSONDecodeError, ToolValidationError) as e:
        result = f"Error: argumentos invalidos para '{name}': {e}"
        log_tool_call(
            name=name,
            args=args,
            permission=tool.permission.value,
            duration_seconds=time.perf_counter() - start,
            status="rejected_invalid_args",
            result=result,
        )
        return result

    try:
        future = _EXECUTOR.submit(tool.handler, **args)
        result = str(future.result(timeout=tool.timeout_seconds))
        status = "ok"
    except FutureTimeoutError:
        result = f"Error: la tool '{name}' supero el timeout de {tool.timeout_seconds}s"
        status = "timeout"
    except Exception as e:
        result = f"Error al ejecutar la tool: {e}"
        status = "error"

    log_tool_call(
        name=name,
        args=args,
        permission=tool.permission.value,
        duration_seconds=time.perf_counter() - start,
        status=status,
        result=result,
    )
    return result


if __name__ == "__main__":
    from agent.tools.spec import Permission, ToolSpec

    # Camino feliz: allowlist + permiso + validacion + ejecucion OK.
    assert "Error" not in execute_tool("list_files", '{"path": "."}')

    # Tool desconocida: rechazada por allowlist.
    assert "no esta en la allowlist" in execute_tool("no_existe", "{}")

    # Argumentos invalidos: falta 'path' (requerido por read_file).
    assert "argumentos invalidos" in execute_tool("read_file", "{}")

    # JSON invalido.
    assert "argumentos invalidos" in execute_tool("read_file", "{not json")

    # Argumento extra no declarado en el schema.
    assert "argumentos invalidos" in execute_tool("read_file", '{"path": "x.txt", "extra": 1}')

    # Permiso no habilitado: se registra una tool falsa de nivel WRITE y se
    # comprueba que execute_tool la rechaza sin llegar a invocar el handler.
    def _handler_no_debe_llamarse(**kwargs):
        raise AssertionError("no deberia ejecutarse: el permiso no esta habilitado")

    _write_tool = ToolSpec(
        name="_fake_write_tool",
        description="tool de prueba de solo autochequeo",
        parameters={"type": "object", "properties": {}},
        handler=_handler_no_debe_llamarse,
        permission=Permission.WRITE,
    )
    registry.ALL_TOOLS.append(_write_tool)
    registry._BY_NAME[_write_tool.name] = _write_tool
    try:
        assert "no habilitado" in execute_tool("_fake_write_tool", "{}")
    finally:
        registry.ALL_TOOLS.remove(_write_tool)
        del registry._BY_NAME[_write_tool.name]

    # Timeout: tool falsa cuyo handler duerme mas que su timeout_seconds.
    def _handler_lento(**kwargs):
        time.sleep(0.3)
        return "no deberia verse"

    _slow_tool = ToolSpec(
        name="_fake_slow_tool",
        description="tool de prueba de solo autochequeo",
        parameters={"type": "object", "properties": {}},
        handler=_handler_lento,
        permission=Permission.READ,
        timeout_seconds=0.05,
    )
    registry.ALL_TOOLS.append(_slow_tool)
    registry._BY_NAME[_slow_tool.name] = _slow_tool
    try:
        assert "supero el timeout" in execute_tool("_fake_slow_tool", "{}")
    finally:
        registry.ALL_TOOLS.remove(_slow_tool)
        del registry._BY_NAME[_slow_tool.name]

    print("OK: agent/tools/executor.py autochequeo pasado")
