"""REPL de linea de comandos para probar el agente de extremo a extremo contra Ollama."""
import openai

from agent.config import OLLAMA_BASE_URL
from agent.loop import run_turn
from agent.memory import Memory
from agent.tools import registry
from agent.tools.executor import execute_tool

SYSTEM_PROMPT = (
    "Eres un agente de IA local que ayuda con tareas sencillas de archivos. "
    "Usa las tools disponibles cuando las necesites."
)


def main():
    """Arranca el REPL: mantiene el historial de conversacion entre turnos.

    Crea el cliente OpenAI apuntando a Ollama y una Memory con el prompt de
    sistema, y por cada linea de entrada del usuario llama a run_turn() para
    ejecutar el ciclo completo del agente e imprime la respuesta final.
    Termina con "salir", "exit" o "quit".
    """
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    memory = Memory(system_prompt=SYSTEM_PROMPT)
    tools_schema = registry.openai_schemas()

    print("Agente listo. Escribe 'salir' para terminar.")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("salir", "exit", "quit", "bye", "adios", "q"):
            break
        if not user_input:
            continue

        memory.append({"role": "user", "content": user_input})
        response = run_turn(client, memory, tools_schema, execute_tool)
        print(response)


if __name__ == "__main__":
    main()


"""
    # Latencia de ejemplo:
        > lee el directorio workspace
        [latencia] vuelta 1: llamada al modelo = 26.31s
        [latencia] tool 'list_files' = 0.001s
        [latencia] vuelta 2: llamada al modelo = 9.63s
        [latencia] turno completo = 35.95s
 """
