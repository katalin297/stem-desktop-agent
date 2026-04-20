from stem.types import MemoryEntry


class Memory:
    def __init__(self) -> None:
        self.entries: list[MemoryEntry] = []

    def add(self, step: int, observation: str) -> None:
        self.entries.append(MemoryEntry(step = step, observation = observation))

    def summary(self) -> str:
        if not self.entries:
            return "No observations yet."

        lines = []
        for entry in self.entries[-10:]:
            lines.append(f"Step {entry.step}: {entry.observation}")

        return "\n".join(lines)