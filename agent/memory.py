class Memory:
    """Historial de mensajes de la conversacion en memoria, sin persistencia en disco.

    Envuelve la lista de mensajes en formato OpenAI (role/content) que se
    pasa tal cual a `client.chat.completions.create(messages=...)`.
    """

    def __init__(self, system_prompt: str | None = None):
        """Inicializa el historial, opcionalmente con un mensaje de sistema inicial.

        Args:
            system_prompt: Texto del mensaje de rol "system" con el que arranca
                la conversacion. Si es None, el historial empieza vacio.
        """
        self._messages: list[dict] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    def append(self, message: dict) -> None:
        """Anade un mensaje al final del historial.

        Args:
            message: Mensaje en formato OpenAI, p. ej. {"role": ..., "content": ...}.
        """
        self._messages.append(message)

    def get(self) -> list[dict]:
        """Devuelve la lista de mensajes acumulados, en orden cronologico.

        Returns:
            Lista de mensajes en formato OpenAI lista para pasar a la API de chat.
        """
        return self._messages
