from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    title: str
    task_type: str
    repo_path: str
    issue: str
    goal: dict
    expected: dict[str, Any] = Field(default_factory = dict)


class ToolResult(BaseModel):
    ok: bool
    command: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    message: str = ""


class MemoryEntry(BaseModel):
    step: int
    observation: str


class ActionOption(BaseModel):
    kind: Literal["run_command", "read_file", "write_file", "finish"]
    value: str = ""
    label: str


class ActionChoice(BaseModel):
    kind: Literal["run_command", "read_file", "write_file", "finish"]
    value: str = ""
    reason: str = ""


class RunState(BaseModel):
    commands_tried: List[str] = Field(default_factory = list)
    files_read: List[str] = Field(default_factory = list)
    observations: List[str] = Field(default_factory = list)
    last_output: str = ""
    finish_requested: bool = False

    edited_files: List[str] = Field(default_factory = list)
    backups: dict[str, str] = Field(default_factory = dict)

    repair_attempted: bool = False
    repair_success: bool = False
    repair_improved: bool = False

    repair_baseline_failures: Optional[int] = None
    repair_result_failures: Optional[int] = None

    last_test_command: Optional[str] = None
    preferred_test_command: Optional[str] = None
    repair_test_command: Optional[str] = None

    patch_diff: str = ""


class FinalReport(BaseModel):
    success: bool
    main_evidence: Optional[str]
    likely_files: List[str]
    summary: str
    task_type: str
    actions_taken: int
    artifact_text: str

    repair_success: bool = False
    repair_improved: bool = False
    edited_files: List[str] = Field(default_factory = list)