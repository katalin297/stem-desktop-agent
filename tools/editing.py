import difflib
import shutil
from pathlib import Path


def backup_file(path: str) -> str:
    source = Path(path)
    backup = source.with_suffix(source.suffix + ".stem_backup")

    counter = 1
    while backup.exists():
        backup = source.with_suffix(source.suffix + f".stem_backup_{counter}")
        counter += 1

    shutil.copy2(source, backup)
    return str(backup)


def restore_backup(path: str, backup_path: str) -> None:
    shutil.copy2(backup_path, path)


def write_text_file(path: str, content: str) -> None:
    Path(path).write_text(content, encoding = "utf-8")


def make_unified_diff(old_text: str, new_text: str, file_path: str) -> str:
    if old_text and not old_text.endswith("\n"):
        old_text += "\n"

    if new_text and not new_text.endswith("\n"):
        new_text += "\n"

    diff = difflib.unified_diff(
        old_text.splitlines(keepends = True),
        new_text.splitlines(keepends = True),
        fromfile = f"{file_path} (before)",
        tofile = f"{file_path} (after)"
    )
    return "".join(diff)