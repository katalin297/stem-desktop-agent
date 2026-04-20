import json
from pathlib import Path

from stem.blueprint import Blueprint
from stem.loaders import load_blueprints


def get_active_blueprint(
    blueprints_path: str = "configs/blueprints.json",
    selected_path: str = "outputs/selected_blueprint.json"
) -> Blueprint:
    blueprints = load_blueprints(blueprints_path)

    selected_file = Path(selected_path)
    if not selected_file.exists():
        return blueprints[0]

    data = json.loads(selected_file.read_text(encoding = "utf-8"))
    selected_name = data.get("selected_blueprint")

    for blueprint in blueprints:
        if blueprint.name == selected_name:
            return blueprint

    return blueprints[0]