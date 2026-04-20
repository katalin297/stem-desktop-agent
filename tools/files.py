from pathlib import Path


def read_file(path: str) -> str:
    return Path(path).read_text(encoding = "utf-8")


def list_files(root: str) -> list[str]:
    root_path = Path(root)
    blocked_parts = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "outputs",
    }

    files: list[str] = []

    for p in root_path.rglob("*"):
        if not p.is_file():
            continue

        if any(part in blocked_parts for part in p.parts):
            continue

        files.append(str(p))

    return files


def find_interesting_files(root: str) -> list[str]:
    files = list_files(root)
    interesting: list[str] = []

    for f in files:
        lowered = f.lower()

        if (
            lowered.endswith("readme.md")
            or lowered.endswith("requirements.txt")
            or lowered.endswith(".py")
            or "test" in lowered
        ):
            interesting.append(f)

    return interesting[:30]