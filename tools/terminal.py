import re
import subprocess
from pathlib import Path

from stem.types import ToolResult


def run_command(command: str, cwd: str) -> ToolResult:
    try:
        result = subprocess.run(
            command,
            shell = True,
            cwd = str(Path(cwd).resolve()),
            capture_output = True,
            text = True,
            timeout = 30
        )

        return ToolResult(
            ok = result.returncode == 0,
            command = command,
            stdout = result.stdout,
            stderr = result.stderr,
            exit_code = result.returncode,
            message = "Command executed"
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok = False,
            command = command,
            message = "Command timed out"
        )
    except Exception as e:
        return ToolResult(
            ok = False,
            command = command,
            message = f"Command failed: {e}"
        )


def is_test_command(command: str) -> bool:
    lowered = command.lower()
    return "pytest" in lowered or "unittest" in lowered


def estimate_failure_count(stdout: str, stderr: str, exit_code: int | None) -> int:
    if exit_code == 0:
        return 0

    text = f"{stdout}\n{stderr}".lower()

    counts: list[int] = []

    patterns = [
        r"(\d+)\s+failed",
        r"(\d+)\s+error",
        r"(\d+)\s+errors",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            counts.append(int(match.group(1)))

    if counts:
        return max(counts)

    if (
        "assertionerror" in text
        or "modulenotfounderror" in text
        or "traceback" in text
        or "error" in text
        or "failed" in text
    ):
        return 1

    return 999