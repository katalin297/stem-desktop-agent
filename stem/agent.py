import json
import os
from pathlib import Path

from dotenv import load_dotenv

from stem.blueprint import Blueprint
from stem.chooser import choose_action_local, choose_action_llm
from stem.memory import Memory
from stem.types import FinalReport, RunState, Task
from task_types import get_task_type
from tools.files import read_file
from tools.terminal import run_command


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

    def execute_action(self, task: Task, choice, state: RunState) -> str:
        if choice.kind == "run_command":
            result = run_command(choice.value, cwd = task.repo_path)

            state.commands_tried.append(choice.value)
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

        state.finish_requested = True
        observation = "Agent chose to finish."
        state.last_output = observation
        state.observations.append(observation)
        return observation

    def run(self, task: Task) -> FinalReport:
        task_type = get_task_type(task.task_type)
        actions = task_type.build_actions(task)
        state = RunState()

        self.memory.add(1, f"Loaded task: {task.title}")
        self.memory.add(2, f"Task type: {task.task_type}")
        self.memory.add(3, f"Blueprint: {self.blueprint.name}")
        self.memory.add(4, f"Chooser mode: {'llm' if self.use_llm else 'local'}")

        for step in range(5, 5 + self.blueprint.max_steps):
            choice = self.choose_action(task, actions, state)
            print(
            f"STEP {step} | chooser={'llm' if self.use_llm else 'local'} | "
            f"kind={choice.kind} | value={choice.value} | reason={choice.reason}"
            )
            self.memory.add(step, f"Chosen action: {choice.kind} | {choice.value} | {choice.reason}")

            observation = self.execute_action(task, choice, state)
            self.memory.add(step, observation[:1200])

            if choice.kind == "finish":
                break

        success, main_evidence = task_type.judge_success(state)
        likely_files = task_type.choose_likely_files(state)

        summary = (
            f"Task type: {task.task_type}. "
            f"Success: {success}. "
            f"Main evidence: {main_evidence}. "
            f"Commands tried: {state.commands_tried}. "
            f"Files read: {likely_files}."
        )

        artifact_text = task_type.build_artifact(
            task = task,
            state = state,
            main_evidence = main_evidence,
            likely_files = likely_files
        )

        return FinalReport(
            success = success,
            main_evidence = main_evidence,
            likely_files = likely_files,
            summary = summary,
            task_type = task.task_type,
            actions_taken = len(state.commands_tried) + len(state.files_read) + (1 if state.finish_requested else 0),
            artifact_text = artifact_text
        )