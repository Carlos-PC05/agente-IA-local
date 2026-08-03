"""Modelo de datos para describir una tool: metadatos + funcion que la implementa."""
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from agent.config import DEFAULT_TOOL_TIMEOUT


class Permission(str, Enum):
    """Nivel de permiso requerido para ejecutar una tool.

    Se compara contra agent.config.ALLOWED_PERMISSION_LEVELS en
    agent/tools/executor.py para decidir si una tool puede ejecutarse.
    """

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclass(frozen=True)
class ToolSpec:
    """Describe una tool disponible para el modelo: su contrato y su implementacion.

    Cada modulo de tools (agent/tools/files.py, y en el futuro notes.py/shell.py)
    expone una lista de ToolSpec. agent/tools/registry.py las agrega en
    ALL_TOOLS, que actua como la allowlist explicita de tools ejecutables.

    Attributes:
        name: Nombre de la tool tal y como lo vera el modelo (debe coincidir
            con el nombre que el modelo usa al pedir la tool-call).
        description: Descripcion en lenguaje natural que se envia al modelo
            para que sepa cuando usar la tool.
        parameters: JSON Schema (formato OpenAI function-calling) de los
            argumentos que acepta la tool. Validado por
            agent/tools/validation.py antes de invocar `handler`.
        handler: Funcion Python que implementa la tool. Recibe los argumentos
            ya parseados como kwargs y devuelve un string (los errores se
            devuelven como texto, no como excepcion).
        permission: Nivel de permiso requerido, ver `Permission`.
        timeout_seconds: Segundos maximos que agent/tools/executor.py espera
            a que `handler` termine antes de reportar un timeout.
    """

    name: str
    description: str
    parameters: dict
    handler: Callable[..., str]
    permission: Permission
    timeout_seconds: float = DEFAULT_TOOL_TIMEOUT


if __name__ == "__main__":
    _spec = ToolSpec(
        name="_prueba",
        description="tool de prueba",
        parameters={"type": "object", "properties": {}},
        handler=lambda: "ok",
        permission=Permission.READ,
    )
    assert _spec.timeout_seconds == DEFAULT_TOOL_TIMEOUT
    assert _spec.permission == "read", "Permission debe compararse igual que su string"
    assert _spec.permission in {"read"}, "Permission debe funcionar dentro de un set de strings"

    print("OK: agent/tools/spec.py autochequeo pasado")
