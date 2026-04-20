from task_types.debugging import DebuggingTaskType
from task_types.research import ResearchTaskType


def get_task_type(name: str):
    mapping = {
        "debugging": DebuggingTaskType(),
        "research": ResearchTaskType(),
    }

    if name not in mapping:
        raise ValueError(f"Unknown task type: {name}")

    return mapping[name]