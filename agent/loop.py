import json

from agent.config import MAX_ITERATIONS, MODEL_NAME

def run_turn(client, memory, tools_schema, tool_dispatch):
    """Ejecuta el ciclo plan -> act -> observe -> refine hasta obtener respuesta final."""
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=memory.get(),
            tools=tools_schema,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            memory.append({"role": "assistant", "content": message.content})
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
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = tool_fn(**args)
                except Exception as e:
                    result = f"Error al ejecutar la tool: {e}"

            memory.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                }
            )

    return "Error: se alcanzo MAX_ITERATIONS sin obtener una respuesta final."
