"""Bucle principal del agente: plan -> act -> observe -> refine."""
import time

from agent.config import MAX_ITERATIONS, MODEL_NAME


def run_turn(client, memory, tools_schema, execute_tool):
    """Ejecuta el ciclo plan-act-observe-refine hasta obtener una respuesta final.

    En cada vuelta pide al modelo el siguiente paso (Plan). Si el modelo pide
    ejecutar tools, delega cada una en `execute_tool` -- que aplica allowlist,
    permisos, validacion de argumentos y timeout antes de correrla (ver
    agent/tools/executor.py) -- y guarda tanto la llamada como su resultado en
    la memoria (Observe) antes de volver a preguntar al modelo (Refine).
    Termina en cuanto el modelo responde sin pedir mas tools, o al superar
    MAX_ITERATIONS vueltas.

    De paso imprime por stdout la latencia de cada llamada al modelo, de
    cada tool y del turno completo, para poder calibrar el rendimiento real
    del hardware sobre el que corre Ollama (ver "Medir latencia real" en
    Plan.md).

    Args:
        client: Cliente `openai.OpenAI` apuntando al endpoint de Ollama.
        memory: Instancia de `Memory` con el historial de la conversacion;
            se muta anadiendo los mensajes de asistente y de tool generados.
        tools_schema: Lista de tools en formato OpenAI (ver
            agent/tools/registry.py:openai_schemas()) que se ofrecen al
            modelo en cada llamada.
        execute_tool: Funcion `(name: str, raw_arguments: str) -> str` que
            ejecuta una tool ya validada y con la capa de seguridad aplicada
            (ver agent/tools/executor.py:execute_tool()). Nunca lanza
            excepciones: cualquier fallo vuelve como string "Error: ...".

    Returns:
        Texto de la respuesta final del modelo, o un mensaje de error si se
        alcanza MAX_ITERATIONS sin que el modelo termine de usar tools.
    """
    turn_start = time.perf_counter()

    for iteration in range(1, MAX_ITERATIONS + 1):
        model_start = time.perf_counter()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=memory.get(),
            tools=tools_schema,
        )
        print(f"[latencia] vuelta {iteration}: llamada al modelo = {time.perf_counter() - model_start:.2f}s")
        message = response.choices[0].message

        if not message.tool_calls:
            memory.append({"role": "assistant", "content": message.content})
            print(f"[latencia] turno completo = {time.perf_counter() - turn_start:.2f}s")
            return message.content

        memory.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        )

        for call in message.tool_calls:
            tool_start = time.perf_counter()
            result = execute_tool(call.function.name, call.function.arguments)
            print(f"[latencia] tool '{call.function.name}' = {time.perf_counter() - tool_start:.3f}s")

            memory.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                }
            )

    print(f"[latencia] turno completo (MAX_ITERATIONS alcanzado) = {time.perf_counter() - turn_start:.2f}s")
    return "Error: se alcanzo MAX_ITERATIONS sin obtener una respuesta final."


if __name__ == "__main__":
    from agent.memory import Memory

    class _FakeFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class _FakeToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.function = _FakeFunction(name, arguments)

    class _FakeMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    class _FakeChoice:
        def __init__(self, message):
            self.message = message

    class _FakeResponse:
        def __init__(self, message):
            self.choices = [_FakeChoice(message)]

    class _FakeCompletions:
        def __init__(self, responses):
            self._responses = list(responses)

        def create(self, **kwargs):
            return self._responses.pop(0)

    class _FakeChat:
        def __init__(self, responses):
            self.completions = _FakeCompletions(responses)

    class _FakeClient:
        """Cliente falso que devuelve respuestas predefinidas, para probar
        run_turn() sin necesitar Ollama corriendo."""

        def __init__(self, responses):
            self.chat = _FakeChat(responses)

    # Escenario 1: el modelo responde directamente, sin pedir tools.
    client_directo = _FakeClient([_FakeResponse(_FakeMessage("hola"))])
    memoria = Memory(system_prompt="sistema")
    memoria.append({"role": "user", "content": "hola"})
    resultado = run_turn(
        client_directo, memoria, tools_schema=[], execute_tool=lambda n, a: "no deberia llamarse"
    )
    assert resultado == "hola"

    # Escenario 2: el modelo pide una tool y luego responde con el resultado.
    llamada_tool = _FakeToolCall("call_1", "list_files", '{"path": "."}')
    respuestas = [
        _FakeResponse(_FakeMessage(None, tool_calls=[llamada_tool])),
        _FakeResponse(_FakeMessage("listo")),
    ]
    client_con_tool = _FakeClient(respuestas)
    memoria2 = Memory(system_prompt="sistema")
    memoria2.append({"role": "user", "content": "lista archivos"})

    llamadas_recibidas = []

    def _execute_tool_falso(name, raw_arguments):
        llamadas_recibidas.append((name, raw_arguments))
        return "a.txt\nb.txt"

    resultado2 = run_turn(client_con_tool, memoria2, tools_schema=[], execute_tool=_execute_tool_falso)
    assert resultado2 == "listo"
    assert llamadas_recibidas == [("list_files", '{"path": "."}')]
    _mensajes_tool = [m for m in memoria2.get() if m.get("role") == "tool"]
    assert len(_mensajes_tool) == 1
    assert _mensajes_tool[0]["content"] == "a.txt\nb.txt"

    print("OK: agent/loop.py autochequeo pasado")
