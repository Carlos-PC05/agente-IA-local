"""Bucle principal del agente: plan -> act -> observe -> refine."""
import json
import time

from agent.config import MAX_ITERATIONS, MODEL_NAME


def run_turn(client, memory, tools_schema, tool_dispatch):
    """Ejecuta el ciclo plan-act-observe-refine hasta obtener una respuesta final.

    En cada vuelta pide al modelo el siguiente paso (Plan). Si el modelo pide
    ejecutar tools, las ejecuta capturando cualquier excepcion como texto de
    error en vez de propagarla (Act), y guarda tanto la llamada como su
    resultado en la memoria (Observe) antes de volver a preguntar al modelo
    (Refine). Termina en cuanto el modelo responde sin pedir mas tools, o al
    superar MAX_ITERATIONS vueltas.

    De paso imprime por stdout la latencia de cada llamada al modelo, de
    cada tool y del turno completo, para poder calibrar el rendimiento real
    del hardware sobre el que corre Ollama (ver "Medir latencia real" en
    Plan.md).

    Args:
        client: Cliente `openai.OpenAI` apuntando al endpoint de Ollama.
        memory: Instancia de `Memory` con el historial de la conversacion;
            se muta anadiendo los mensajes de asistente y de tool generados.
        tools_schema: Lista de tools en formato OpenAI (ver TOOL_SCHEMAS en
            agent/tools/files.py) que se ofrecen al modelo en cada llamada.
        tool_dispatch: Diccionario nombre de tool -> funcion Python que la
            implementa (ver TOOL_DISPATCH en agent/tools/files.py).

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
            tool_fn = tool_dispatch.get(call.function.name)
            if tool_fn is None:
                result = f"Error: tool desconocida '{call.function.name}'"
            else:
                tool_start = time.perf_counter()
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = tool_fn(**args)
                except Exception as e:
                    result = f"Error al ejecutar la tool: {e}"
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
