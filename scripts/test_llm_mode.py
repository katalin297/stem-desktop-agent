from stem.select_blueprint import get_active_blueprint
from stem.agent import StemAgent


def main() -> None:
    blueprint = get_active_blueprint()
    agent = StemAgent(blueprint = blueprint)

    task = agent.load_task("benchmark/tasks/task_02.json")
    report = agent.run(task)

    print("Blueprint:", blueprint.name)
    print("Task type:", report.task_type)
    print("Success:", report.success)
    print("Actions:", report.actions_taken)
    print("\nArtifact:\n")
    print(report.artifact_text)


if __name__ == "__main__":
    main()