from collections import defaultdict


class MemoryService:
    def __init__(self, limit: int = 5) -> None:
        self.history: dict[str, list[dict[str, str]]] = defaultdict(list)
        self.limit = limit

    def get_history(self, session_id: str) -> str:
        messages = self.history[session_id]
        if not messages:
            return "No previous conversation."

        return "\n".join(f"{m['role']}: {m['content']}" for m in messages)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.history[session_id].append({"role": role, "content": content})
        if len(self.history[session_id]) > self.limit:
            self.history[session_id].pop(0)
