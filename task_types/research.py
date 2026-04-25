from pathlib import Path

from task_types.base import TaskType
from stem.types import ActionOption, RunState, Task
from tools.files import list_files, read_file


class ResearchTaskType(TaskType):
    name = "research"

    def build_actions(self, task: Task) -> list[ActionOption]:
        actions: list[ActionOption] = []

        files = list_files(task.repo_path)
        for file_path in files:
            lowered = file_path.lower()
            if lowered.endswith(".md") or lowered.endswith(".txt"):
                actions.append(
                    ActionOption(
                        kind = "read_file",
                        value = file_path,
                        label = f"Read {file_path.split('/')[-1]}"
                    )
                )

        actions = actions[:10]
        actions.append(ActionOption(kind = "finish", value = "", label = "Finish"))
        return actions

    def judge_success(self, task: Task, state: RunState) -> tuple[bool, str | None]:
        if state.finish_requested and len(state.files_read) >= 2:
            return True, f"Read {len(state.files_read)} files and finished"

        return False, None

    def choose_likely_files(self, task: Task, state: RunState) -> list[str]:
        return state.files_read[:5]

    def build_artifact(
        self,
        task: Task,
        state: RunState,
        main_evidence: str | None,
        likely_files: list[str]
    ) -> str:
        snippets: list[str] = []

        for file_path in state.files_read[:3]:
            try:
                text = read_file(file_path).strip().replace("\n", " ")
                short = text[:180].strip()
                snippets.append(f"- {Path(file_path).name}: {short}")
            except Exception:
                snippets.append(f"- {Path(file_path).name}: could not read content")

        lines = [
            "Research brief",
            f"Task: {task.title}",
            "Key points:",
        ]
        lines.extend(snippets)

        lines.append("Takeaway:")
        lines.append(
            "A good agent should keep compact memory, recover by checking assumptions when tools fail, "
            "and stop when it has enough evidence instead of exploring forever."
        )

        return "\n".join(lines)