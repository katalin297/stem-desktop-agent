import json
import sys
from pathlib import Path

from stem.agent import StemAgent
from stem.select_blueprint import get_active_blueprint


def main() -> None:
    task_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "benchmark/tasks/task_01.json"
    )

    blueprint = get_active_blueprint()

    agent = StemAgent(blueprint = blueprint)
    task = agent.load_task(task_path)
    report = agent.run(task)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok = True)

    output_path = output_dir / f"{task.id}_{blueprint.name}.json"
    output_path.write_text(
        json.dumps(report.model_dump(), indent = 2),
        encoding = "utf-8"
    )

    artifact_path = output_dir / f"{task.id}_{blueprint.name}_artifact.txt"
    artifact_path.write_text(report.artifact_text, encoding = "utf-8")

    print("\n=== FINAL REPORT ===")
    print(f"Blueprint: {blueprint.name}")
    print(f"Task type: {report.task_type}")
    print(f"Success: {report.success}")
    print(f"Main evidence: {report.main_evidence}")
    print(f"Likely files: {report.likely_files}")
    print(f"Actions taken: {report.actions_taken}")
    print(f"Summary: {report.summary}")
    print("\n=== ARTIFACT ===")
    print(report.artifact_text)
    print(f"\nSaved report to: {output_path}")
    print(f"Saved artifact to: {artifact_path}")


if __name__ == "__main__":
    main()