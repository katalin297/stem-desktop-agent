import json
from pathlib import Path

from stem.agent import StemAgent
from stem.loaders import load_blueprints


TRAIN_TASKS = [
    "benchmark/tasks/task_01.json",
    "benchmark/tasks/task_02.json",
    "benchmark/tasks/task_03.json",
]

TEST_TASKS = [
    "benchmark/tasks/task_04.json",
    "benchmark/tasks/task_05.json",
]


def score_task(task, report) -> dict:
    expected = task.expected
    score = 0.0
    max_score = 0.0
    notes = []

    if "success" in expected:
        max_score += 1
        if report.success == expected["success"]:
            score += 1
        else:
            notes.append("success mismatch")

    if "main_evidence_contains" in expected:
        max_score += 1
        target = expected["main_evidence_contains"]
        if report.main_evidence and target in report.main_evidence:
            score += 1
        else:
            notes.append("main evidence mismatch")

    if "likely_files_should_include" in expected:
        needed = expected["likely_files_should_include"]
        max_score += len(needed)

        for item in needed:
            if item in report.likely_files:
                score += 1
            else:
                notes.append(f"missing likely file: {item}")

    if "minimum_files_read" in expected:
        max_score += 1
        if len(report.likely_files) >= expected["minimum_files_read"]:
            score += 1
        else:
            notes.append("not enough files read")
    
    if "artifact_should_contain" in expected:
        needed_terms = expected["artifact_should_contain"]
        max_score += len(needed_terms)

        artifact_lower = report.artifact_text.lower()
        for term in needed_terms:
            if term.lower() in artifact_lower:
                score += 1
            else:
                notes.append(f"artifact missing term: {term}")

    return {
        "score": score,
        "max_score": max_score,
        "notes": notes,
    }


def evaluate_blueprint(blueprint, task_paths):
    agent = StemAgent(blueprint = blueprint)
    total_score = 0.0
    total_max = 0.0
    total_actions = 0
    rows = []

    for task_path in task_paths:
        task = agent.load_task(task_path)
        report = agent.run(task)
        scored = score_task(task, report)

        total_score += scored["score"]
        total_max += scored["max_score"]
        total_actions += report.actions_taken

        rows.append({
            "blueprint": blueprint.name,
            "task_id": task.id,
            "task_type": task.task_type,
            "success": report.success,
            "main_evidence": report.main_evidence,
            "likely_files": report.likely_files,
            "actions_taken": report.actions_taken,
            "score": scored["score"],
            "max_score": scored["max_score"],
            "notes": scored["notes"],
        })

    return {
        "rows": rows,
        "total_score": total_score,
        "total_max": total_max,
        "total_actions": total_actions,
    }


def main() -> None:
    blueprints = load_blueprints("configs/blueprints.json")

    train_totals = []
    all_train_rows = []

    for blueprint in blueprints:
        result = evaluate_blueprint(blueprint, TRAIN_TASKS)
        train_totals.append({
            "blueprint": blueprint.name,
            "train_score": result["total_score"],
            "train_max": result["total_max"],
            "train_actions": result["total_actions"],
        })
        all_train_rows.extend(result["rows"])

    train_totals.sort(
        key = lambda x: (-x["train_score"], x["train_actions"])
    )

    winner_name = train_totals[0]["blueprint"]
    winner_blueprint = next(bp for bp in blueprints if bp.name == winner_name)

    test_result = evaluate_blueprint(winner_blueprint, TEST_TASKS)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok = True)

    (output_dir / "train_results.json").write_text(
        json.dumps(all_train_rows, indent = 2),
        encoding = "utf-8"
    )

    (output_dir / "train_totals.json").write_text(
        json.dumps(train_totals, indent = 2),
        encoding = "utf-8"
    )

    (output_dir / "selected_blueprint.json").write_text(
        json.dumps({"selected_blueprint": winner_name}, indent = 2),
        encoding = "utf-8"
    )

    (output_dir / "test_results.json").write_text(
        json.dumps(test_result["rows"], indent = 2),
        encoding = "utf-8"
    )

    (output_dir / "test_totals.json").write_text(
        json.dumps({
            "blueprint": winner_name,
            "test_score": test_result["total_score"],
            "test_max": test_result["total_max"],
            "test_actions": test_result["total_actions"],
        }, indent = 2),
        encoding = "utf-8"
    )

    print("\n=== TRAIN TOTALS ===")
    for row in train_totals:
        print(row)

    print("\n=== SELECTED BLUEPRINT ===")
    print(winner_name)

    print("\n=== TEST TOTALS ===")
    print({
        "blueprint": winner_name,
        "test_score": test_result["total_score"],
        "test_max": test_result["total_max"],
        "test_actions": test_result["total_actions"],
    })


if __name__ == "__main__":
    main()