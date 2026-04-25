import json
import os
from pathlib import Path

from dotenv import load_dotenv

from stem.blueprint import Blueprint
from stem.chooser import choose_action_local, choose_action_llm
from stem.memory import Memory
from stem.repair import generate_repaired_file
from stem.types import FinalReport, RunState, Task
from task_types import get_task_type
from tools.editing import backup_file, make_unified_diff, restore_backup, write_text_file
from tools.files import read_file
from tools.terminal import estimate_failure_count, is_test_command, run_command
from tools.workspace import prepare_runtime_repo


class StemAgent:
    def __init__(self, blueprint: Blueprint) -> None:
        self.memory = Memory()
        self.blueprint = blueprint

        load_dotenv(override = True)
        self.use_llm = os.getenv("USE_LLM", "0") == "1"

    def load_task(self, task_path: str) -> Task:
        data = json.loads(Path(task_path).read_text(encoding = "utf-8"))
        return Task(**data)

    def choose_action(self, task: Task, actions, state: RunState):
        if self.use_llm:
            return choose_action_llm(
                task = task,
                actions = actions,
                state = state,
                blueprint = self.blueprint,
                memory_summary = self.memory.summary()
            )

        return choose_action_local(
            task = task,
            actions = actions,
            state = state,
            blueprint = self.blueprint
        )

    def _prepare_runtime_task(self, task: Task) -> Task:
        runtime_repo_path = prepare_runtime_repo(task.id, self.blueprint.name, task.repo_path)
        return task.model_copy(update = {"repo_path": runtime_repo_path})

    def _normalize_path(self, path: str, runtime_root: str, original_root: str) -> str:
        return path.replace(runtime_root, original_root)

    def _normalize_text(self, text: str, runtime_root: str, original_root: str) -> str:
        return text.replace(runtime_root, original_root)

    def _normalize_state_for_display(self, state: RunState, runtime_root: str, original_root: str) -> RunState:
        return RunState(
            commands_tried = state.commands_tried.copy(),
            files_read = [self._normalize_path(path, runtime_root, original_root) for path in state.files_read],
            observations = [self._normalize_text(obs, runtime_root, original_root) for obs in state.observations],
            last_output = self._normalize_text(state.last_output, runtime_root, original_root),
            finish_requested = state.finish_requested,
            edited_files = [self._normalize_path(path, runtime_root, original_root) for path in state.edited_files],
            backups = {},
            repair_attempted = state.repair_attempted,
            repair_success = state.repair_success,
            repair_improved = state.repair_improved,
            repair_baseline_failures = state.repair_baseline_failures,
            repair_result_failures = state.repair_result_failures,
            last_test_command = state.last_test_command,
            preferred_test_command = state.preferred_test_command,
            repair_test_command = state.repair_test_command,
            patch_diff = self._normalize_text(state.patch_diff, runtime_root, original_root),
        )

    def execute_action(self, task: Task, choice, state: RunState) -> str:
        if choice.kind == "run_command":
            result = run_command(choice.value, cwd = task.repo_path)

            state.commands_tried.append(choice.value)

            if is_test_command(choice.value):
                state.last_test_command = choice.value

                if result.exit_code != 0:
                    state.preferred_test_command = choice.value
                    state.repair_baseline_failures = estimate_failure_count(
                        result.stdout,
                        result.stderr,
                        result.exit_code
                    )

            observation = (
                f"Command: {choice.value}\n"
                f"Exit code: {result.exit_code}\n"
                f"STDOUT:\n{result.stdout[:1500]}\n"
                f"STDERR:\n{result.stderr[:1500]}"
            )

            state.last_output = observation
            state.observations.append(observation)
            return observation

        if choice.kind == "read_file":
            content = read_file(choice.value)[:3000]

            state.files_read.append(choice.value)
            observation = f"Read file: {choice.value}\n{content}"

            state.last_output = observation
            state.observations.append(observation)
            return observation

        if choice.kind == "write_file":
            current_content = read_file(choice.value)
            backup_path = backup_file(choice.value)

            state.backups[choice.value] = backup_path
            state.repair_attempted = True

            if choice.value not in state.edited_files:
                state.edited_files.append(choice.value)

            repaired_content = generate_repaired_file(
                task = task,
                target_file = choice.value,
                current_content = current_content,
                state = state,
                model = self.blueprint.model
            )

            if repaired_content == current_content:
                observation = (
                    f"Attempted repair in file: {choice.value}\n"
                    "Patch generation returned identical content. No change was applied."
                )
                state.last_output = observation
                state.observations.append(observation)
                return observation

            write_text_file(choice.value, repaired_content)

            diff = make_unified_diff(current_content, repaired_content, choice.value)
            state.patch_diff = diff[:2000]

            repair_command = state.preferred_test_command or state.last_test_command or "python -m pytest -q"
            repair_result = run_command(repair_command, cwd = task.repo_path)

            state.commands_tried.append(repair_command)
            state.repair_test_command = repair_command
            state.repair_result_failures = estimate_failure_count(
                repair_result.stdout,
                repair_result.stderr,
                repair_result.exit_code
            )

            baseline_failures = state.repair_baseline_failures if state.repair_baseline_failures is not None else 999

            state.repair_improved = (
                repair_result.exit_code == 0
                or state.repair_result_failures < baseline_failures
            )

            state.repair_success = repair_result.exit_code == 0

            rollback_applied = False
            if not state.repair_improved:
                restore_backup(choice.value, backup_path)
                rollback_applied = True

            observation = (
                f"Attempted repair in file: {choice.value}\n"
                f"Repair test command: {repair_command}\n"
                f"Repair exit code: {repair_result.exit_code}\n"
                f"Repair improved: {state.repair_improved}\n"
                f"Repair success: {state.repair_success}\n"
                f"Rollback applied: {rollback_applied}\n"
                f"Applied diff:\n{state.patch_diff[:1200]}\n"
                f"Repair STDOUT:\n{repair_result.stdout[:1200]}\n"
                f"Repair STDERR:\n{repair_result.stderr[:1200]}"
            )

            state.last_output = observation
            state.observations.append(observation)
            return observation

        state.finish_requested = True
        observation = "Agent chose to finish."
        state.last_output = observation
        state.observations.append(observation)
        return observation

    def run(self, task: Task) -> FinalReport:
        runtime_task = self._prepare_runtime_task(task)

        task_type = get_task_type(runtime_task.task_type)
        actions = task_type.build_actions(runtime_task)
        state = RunState()

        self.memory.add(1, f"Loaded task: {task.title}")
        self.memory.add(2, f"Task type: {task.task_type}")
        self.memory.add(3, f"Blueprint: {self.blueprint.name}")
        self.memory.add(4, f"Chooser mode: {'llm' if self.use_llm else 'local'}")

        for step in range(5, 5 + self.blueprint.max_steps):
            choice = self.choose_action(runtime_task, actions, state)
            print(
                f"STEP {step} | chooser={'llm' if self.use_llm else 'local'} | "
                f"kind={choice.kind} | value={choice.value} | reason={choice.reason}"
            )
            self.memory.add(step, f"Chosen action: {choice.kind} | {choice.value} | {choice.reason}")

            observation = self.execute_action(runtime_task, choice, state)
            self.memory.add(step, observation[:1200])

            if choice.kind == "finish":
                break

        display_state = self._normalize_state_for_display(
            state = state,
            runtime_root = runtime_task.repo_path,
            original_root = task.repo_path
        )

        success, main_evidence = task_type.judge_success(task, display_state)
        likely_files = task_type.choose_likely_files(task, display_state)

        summary = (
            f"Task type: {task.task_type}. "
            f"Success: {success}. "
            f"Main evidence: {main_evidence}. "
            f"Commands tried: {display_state.commands_tried}. "
            f"Files read: {display_state.files_read}. "
            f"Edited files: {display_state.edited_files}. "
            f"Repair success: {display_state.repair_success}."
        )

        artifact_text = task_type.build_artifact(
            task = task,
            state = display_state,
            main_evidence = main_evidence,
            likely_files = likely_files
        )

        return FinalReport(
            success = success,
            main_evidence = main_evidence,
            likely_files = likely_files,
            summary = summary,
            task_type = task.task_type,
            actions_taken = (
                len(display_state.commands_tried)
                + len(display_state.files_read)
                + len(display_state.edited_files)
                + (1 if display_state.finish_requested else 0)
            ),
            artifact_text = artifact_text,
            repair_success = display_state.repair_success,
            repair_improved = display_state.repair_improved,
            edited_files = display_state.edited_files
        )