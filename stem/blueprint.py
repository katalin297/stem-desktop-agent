from pydantic import BaseModel


class Blueprint(BaseModel):
    name: str
    model: str = "gpt-5.4"
    max_steps: int = 6
    memory_mode: str = "rolling_summary"

    debugging_start_mode: str = "run_first"
    debugging_files_after_failure: int = 2

    research_min_files: int = 3