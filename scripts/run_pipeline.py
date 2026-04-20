import subprocess
import sys


def run_step(command: list[str]) -> None:
    print(f"\n>>> Running: {' '.join(command)}")
    result = subprocess.run(command)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    run_step([sys.executable, "-m", "eval.run_eval"])
    run_step([sys.executable, "main.py", "benchmark/tasks/task_04.json"])
    run_step([sys.executable, "main.py", "benchmark/tasks/task_05.json"])


if __name__ == "__main__":
    main()