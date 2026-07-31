import openai

from agent.config import OLLAMA_BASE_URL
from agent.loop import run_turn
from agent.memory import Memory
from agent.tools.files import TOOL_DISPATCH, TOOL_SCHEMAS

SYSTEM_PROMPT = (
    "Eres un agente de IA local que ayuda con tareas sencillas de archivos. "
    "Usa las tools disponibles cuando las necesites."
)


def main():
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    memory = Memory(system_prompt=SYSTEM_PROMPT)

    print("Agente listo. Escribe 'salir' para terminar.")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            break
        if not user_input:
            continue

        memory.append({"role": "user", "content": user_input})
        response = run_turn(client, memory, TOOL_SCHEMAS, TOOL_DISPATCH)
        print(response)


if __name__ == "__main__":
    main()
