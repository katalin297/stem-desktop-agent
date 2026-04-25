from pathlib import Path

from task_types.base import TaskType
from stem.types import ActionOption, RunState, Task
from tools.files import find_interesting_files


class DebuggingTaskType(TaskType):
    name = "debugging"

    def build_actions(self, task: Task) -> list[ActionOption]:
        actions = [
            ActionOption(kind = "run_command", value = "pytest -q", label = "Run pytest quietly"),
            ActionOption(kind = "run_command", value = "python -m pytest -q", label = "Run pytest through python"),
            ActionOption(kind = "run_command", value = "pytest", label = "Run pytest"),
            ActionOption(kind = "run_command", value = "python -m unittest", label = "Run unittest"),
        ]

        interesting_files = find_interesting_files(task.repo_path)[:8]

        for file_path in interesting_files:
            actions.append(
                ActionOption(
                    kind = "read_file",
                    value = file_path,
                    label = f"Read {Path(file_path).name}"
                )
            )

        if task.goal.get("repair_code"):
            for file_path in interesting_files:
                lowered = file_path.lower()
                file_name = Path(file_path).name.lower()

                if lowered.endswith(".py") and "test" not in file_name:
                    actions.append(
                        ActionOption(
                            kind = "write_file",
                            value = file_path,
                            label = f"Repair {Path(file_path).name}"
                        )
                    )

        actions.append(ActionOption(kind = "finish", value = "", label = "Finish"))
        return actions

    def judge_success(self, task: Task, state: RunState) -> tuple[bool, str | None]:
        if task.goal.get("repair_code"):
            if state.repair_success:
                return True, state.repair_test_command or state.preferred_test_command
            return False, state.repair_test_command or state.preferred_test_command

        for observation in reversed(state.observations):
            lowered = observation.lower()
            if (
                "traceback" in lowered
                or "assert" in lowered
                or "failed" in lowered
                or "error" in lowered
            ):
                evidence = state.preferred_test_command or (state.commands_tried[-1] if state.commands_tried else None)
                return True, evidence

        return False, None

    def choose_likely_files(self, task: Task, state: RunState) -> list[str]:
        if task.goal.get("repair_code") and state.edited_files:
            combined = state.edited_files + [
                path for path in state.files_read
                if "test" in Path(path).name.lower()
            ]

            deduped = list(dict.fromkeys(combined))
            return deduped[:5]

        lowered = " ".join(state.observations).lower()
        likely_files: list[str] = []

        for file_path in state.files_read:
            file_name = Path(file_path).name.lower()
            if file_name in lowered or "test" in file_name:
                likely_files.append(file_path)

        if not likely_files:
            likely_files = state.files_read[:3]

        return likely_files[:5]

    def build_artifact(
        self,
        task: Task,
        state: RunState,
        main_evidence: str | None,
        likely_files: list[str]
    ) -> str:
        if task.goal.get("repair_code"):
            lines = [
                "Debug repair report",
                f"Task: {task.title}",
                f"Repair attempted: {'yes' if state.repair_attempted else 'no'}",
                f"Repair success: {'yes' if state.repair_success else 'no'}",
                f"Repair improved: {'yes' if state.repair_improved else 'no'}",
                f"Repair command: {state.repair_test_command if state.repair_test_command else 'none'}",
                "Edited files:",
            ]

            if state.edited_files:
                for path in state.edited_files:
                    lines.append(f"- {path}")
            else:
                lines.append("- none")

            if likely_files:
                lines.append("Likely relevant files:")
                for path in likely_files:
                    lines.append(f"- {path}")

            if state.patch_diff:
                lines.append("Patch diff:")
                lines.append(state.patch_diff[:1000])

            useful_observation = None
            for observation in reversed(state.observations):
                if "Repair test command:" in observation or "Command:" in observation:
                    useful_observation = observation[:700]
                    break

            if useful_observation:
                lines.append("Observed output snippet:")
                lines.append(useful_observation)

            return "\n".join(lines)

        lines = [
            "Debug triage report",
            f"Task: {task.title}",
            f"Reproduced: {'yes' if main_evidence else 'no'}",
            f"Main command: {main_evidence if main_evidence else 'none'}",
            "Likely files:",
        ]

        if likely_files:
            for path in likely_files:
                lines.append(f"- {path}")
        else:
            lines.append("- none identified")

        useful_observation = None
        for observation in reversed(state.observations):
            if observation.strip() != "Agent chose to finish.":
                useful_observation = observation[:500]
                break

        if useful_observation:
            lines.append("Observed output snippet:")
            lines.append(useful_observation)

        return "\n".join(lines)