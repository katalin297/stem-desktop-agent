from abc import ABC, abstractmethod

from stem.types import ActionOption, RunState, Task


class TaskType(ABC):
    name: str

    @abstractmethod
    def build_actions(self, task: Task) -> list[ActionOption]:
        pass

    @abstractmethod
    def judge_success(self, task: Task, state: RunState) -> tuple[bool, str | None]:
        pass

    @abstractmethod
    def choose_likely_files(self, task: Task, state: RunState) -> list[str]:
        pass

    @abstractmethod
    def build_artifact(
        self,
        task: Task,
        state: RunState,
        main_evidence: str | None,
        likely_files: list[str]
    ) -> str:
        pass