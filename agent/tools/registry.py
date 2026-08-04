"""Registro central de tools: la allowlist explicita de lo que el agente puede ejecutar."""
from agent.tools.files import FILES_TOOLS
from agent.tools.notes import NOTES_TOOLS
from agent.tools.shell import SHELL_TOOLS
from agent.tools.spec import ToolSpec

# Lista literal de tools habilitadas. Una tool solo es ejecutable si esta
# aqui: no hay resolucion dinamica ni registro implicito. Anadir una tool
# nueva es un cambio de codigo explicito en esta lista.
ALL_TOOLS: list[ToolSpec] = [*FILES_TOOLS, *NOTES_TOOLS, *SHELL_TOOLS]

_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


def get(name: str) -> ToolSpec | None:
    """Busca una tool registrada por nombre.

    Args:
        name: Nombre de la tool, tal y como la pide el modelo en una tool-call.

    Returns:
        El ToolSpec correspondiente, o None si `name` no esta en la allowlist.
    """
    return _BY_NAME.get(name)


def openai_schemas() -> list[dict]:
    """Genera la lista de tools en formato OpenAI a partir de ALL_TOOLS.

    Returns:
        Lista lista para pasar como `tools=` a
        `client.chat.completions.create()`, una entrada por tool registrada.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in ALL_TOOLS
    ]


if __name__ == "__main__":
    assert get("list_files") is not None, "list_files deberia estar registrada"
    assert get("no_existe") is None, "una tool no registrada debe devolver None"

    schemas = openai_schemas()
    assert len(schemas) == len(ALL_TOOLS)
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == ALL_TOOLS[0].name

    print("OK: agent/tools/registry.py autochequeo pasado")
