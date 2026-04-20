import json
from pathlib import Path

from stem.blueprint import Blueprint


def load_blueprints(path: str) -> list[Blueprint]:
    data = json.loads(Path(path).read_text(encoding = "utf-8"))
    return [Blueprint(**item) for item in data]