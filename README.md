# Stem Desktop Agent

A small LLM-driven stem agent that starts from a general task-solving loop, evaluates different behavior blueprints, and specializes its behavior through measurement.

The agent is tested on debugging, research, and one-file repair tasks. In the repair setting, it can reproduce a failing test, inspect relevant files, edit one implementation file, rerun tests, and keep the patch only if the result improves.

## What this project is

This is not a chatbot and not a universal autonomous agent.

It is a task-running agent loop. Given a task, a set of tools, and a blueprint, it repeatedly chooses one action, observes the result, updates memory, and decides whether to continue or stop.

The main idea is that the same stem loop can be used across different task types, while the selected blueprint controls how the agent behaves.

## Main features

- LLM-driven action selection
- Local fallback chooser when the LLM returns invalid JSON
- Blueprint comparison and automatic selection
- Train/test split for evaluation
- Debugging triage reports
- Research brief generation
- One-file code repair
- Backup and rollback before editing files
- Test-based repair verification
- Runtime repository copies so original benchmark repos remain unchanged

## Task types

### Debugging triage

The agent reproduces a failing test, reads likely files, and produces a triage report.

### Research

The agent reads local notes and produces a short brief.

### One-file repair

The agent reproduces a failure, reads relevant files, edits one implementation file, reruns tests, and keeps the patch only if the test result improves.

## How the stem agent works

At a high level:

1. Load a task JSON file.
2. Prepare a runtime copy of the target repo.
3. Build the allowed actions for the task.
4. Ask the chooser for the next action.
5. Execute the selected action.
6. Store observations in memory.
7. Stop when the task is complete.
8. Produce a task-specific artifact.

For repair tasks, the `write_file` action automatically:

1. backs up the target file,
2. asks the model for a full replacement file,
3. writes the file,
4. reruns `python -m pytest -q`,
5. keeps the patch only if the test result improves,
6. restores the backup otherwise.

## Blueprints

The project compares several blueprints:

- `baseline_general`
- `inspect_first`
- `fast_finish`

Each blueprint changes behavior parameters such as:

- whether to run tests first or inspect files first,
- how many files to read after a failure,
- how many research sources to read,
- maximum number of steps.

The evaluator scores each blueprint on training tasks, selects the best one, then tests it on held-out tasks.

## Results

Latest LLM repair run:

| Split | Score |
|---|---:|
| Train | 18 / 18 |
| Test | 14 / 14 |

Selected blueprint:

```text
fast_finish
```

The held-out repair task successfully repaired `list_utils.py`:

```diff
def first_item(items):
-    return items[1]
+    return items[0]
```

The repair was verified by rerunning tests:

```text
1 passed
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENAI_API_KEY=your_key_here
USE_LLM=1
```

To run without the LLM chooser:

```env
USE_LLM=0
```

## Run the full pipeline

```bash
python -m scripts.run_pipeline
python -m scripts.make_summary
```

## Run evaluation only

```bash
python -m eval.run_eval
```

## Run individual tasks

Debugging triage:

```bash
python main.py benchmark/tasks/task_01.json
```

Research:

```bash
python main.py benchmark/tasks/task_02.json
```

One-file repair:

```bash
python main.py benchmark/tasks/task_06.json
python main.py benchmark/tasks/task_07.json
```

## Important files

```text
stem/agent.py          Main agent loop
stem/chooser.py        Local and LLM action choosers
stem/repair.py         LLM-based file repair generation
stem/types.py          Task, action, state, and report types
task_types/            Task-specific action builders and artifacts
tools/                 Terminal, file, editing, and workspace tools
eval/run_eval.py       Blueprint evaluation and selection
benchmark/tasks/       Task definitions
benchmark/repos/       Small benchmark repositories
results/               Saved experiment results
```

## Design decisions

### Why one-file repair only?

I intentionally limited repair to one edited file. This makes the repair loop easier to verify and safer to roll back. Multi-file repair would be a natural next step, but I avoided it in this version to keep the evaluation reliable.

### Why runtime repo copies?

The agent edits only copied repositories inside `.stem_runtime/`. The original benchmark repositories stay unchanged, so evaluation can be rerun safely.

### Why guards around the LLM chooser?

The LLM sometimes tried to finish too early or returned invalid JSON. I added guards to prevent early stopping before required progress, especially for research and repair tasks.

## What failed and what changed

Some failures during development:

- The LLM was sometimes too eager to stop after reproducing a failure.
- The LLM occasionally returned invalid JSON, so I added a local fallback.
- Runtime repos were first copied into `outputs/`, but the file scanner ignored `outputs/`, so the agent could not see files.
- Runtime copies were moved to `.stem_runtime/`.
- `pytest -q` sometimes caused import issues in the runtime setup, so repair verification now uses `python -m pytest -q`.
- One repair generated the correct patch but was rolled back because the verification command was wrong.
- Fixing the verification command made the repair succeed.

## Limitations

- Repair is limited to one file.
- Benchmarks are small and synthetic.
- The agent does not control a full desktop environment.
- The research task uses local notes, not live web browsing.
- The LLM chooser still needs guardrails to avoid premature stopping.

## Future work

- Extend repair to two related files with rollback.
- Add richer project setup and QA tasks.
- Add stronger benchmark cases.
- Add browser or desktop tools as optional capabilities.
- Improve scoring beyond exact expected files and keyword checks.