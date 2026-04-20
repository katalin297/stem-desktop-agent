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