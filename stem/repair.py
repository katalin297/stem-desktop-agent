from pathlib import Path

from stem.llm import ask_model
from stem.types import RunState, Task
from tools.files import read_file


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    return cleaned


def generate_repaired_file(
    task: Task,
    target_file: str,
    current_content: str,
    state: RunState,
    model: str
) -> str:
    related_chunks: list[str] = []

    for file_path in state.files_read[:4]:
        if file_path == target_file:
            continue

        try:
            text = read_file(file_path)[:1600]
            related_chunks.append(f"FILE: {file_path}\n{text}")
        except Exception:
            continue

    last_test_observation = ""
    for observation in reversed(state.observations):
        if "Command:" in observation and ("pytest" in observation or "unittest" in observation):
            last_test_observation = observation[:2500]
            break

    system_prompt = (
        "You repair small Python bugs. "
        "Return ONLY the full replacement contents of the target file. "
        "Do not use markdown fences. "
        "Do the minimal change needed to fix the failing tests. "
        "Preserve unrelated code."
    )

    user_prompt = f"""
Task: {task.title}
Issue: {task.issue}
Goal: {task.goal}

Target file:
{target_file}

Current file contents:
{current_content}

Latest failing test context:
{last_test_observation}

Other related files:
{chr(10).join(related_chunks) if related_chunks else "None"}

Return only the full new contents of the target file.
"""

    repaired = ask_model(
        system_prompt = system_prompt,
        user_prompt = user_prompt,
        model = model
    )

    repaired = _strip_code_fences(repaired)

    if not repaired.strip():
        return current_content

    if current_content.endswith("\n") and not repaired.endswith("\n"):
        repaired += "\n"

    return repaired