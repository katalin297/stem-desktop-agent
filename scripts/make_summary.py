import json
from pathlib import Path


def main() -> None:
    output_dir = Path("outputs")

    train_totals = json.loads((output_dir / "train_totals.json").read_text(encoding = "utf-8"))
    selected = json.loads((output_dir / "selected_blueprint.json").read_text(encoding = "utf-8"))
    test_totals = json.loads((output_dir / "test_totals.json").read_text(encoding = "utf-8"))

    lines = []
    lines.append("Experiment summary")
    lines.append("")
    lines.append("Training results:")
    for row in train_totals:
        lines.append(
            f"- {row['blueprint']}: score {row['train_score']}/{row['train_max']}, "
            f"actions {row['train_actions']}"
        )

    lines.append("")
    lines.append(f"Selected blueprint: {selected['selected_blueprint']}")
    lines.append(
        f"Test results: {test_totals['test_score']}/{test_totals['test_max']}, "
        f"actions {test_totals['test_actions']}"
    )

    summary_path = output_dir / "experiment_summary.txt"
    summary_path.write_text("\n".join(lines), encoding = "utf-8")

    print(f"Saved summary to: {summary_path}")


if __name__ == "__main__":
    main()