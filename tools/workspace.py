import shutil
import uuid
from pathlib import Path


def prepare_runtime_repo(task_id: str, blueprint_name: str, original_repo_path: str) -> str:
    base = Path(".stem_runtime")
    base.mkdir(parents = True, exist_ok = True)

    destination = base / f"{task_id}_{blueprint_name}_{uuid.uuid4().hex[:8]}"

    shutil.copytree(
        Path(original_repo_path),
        destination,
        ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".venv")
    )

    return str(destination)