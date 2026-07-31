class Memory:
    """Historial de mensajes en memoria, sin persistencia en disco."""

    def __init__(self, system_prompt: str | None = None):
        self._messages: list[dict] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    def append(self, message: dict) -> None:
        self._messages.append(message)

    def get(self) -> list[dict]:
        return self._messages
