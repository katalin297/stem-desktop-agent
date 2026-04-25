# Building a Stem Agent for Debugging, Research, and Verified One-File Repair

## 1. Approach

I interpreted the stem-agent task as building a general task-solving loop that can become specific through evaluation, rather than as building one fixed hand-written agent. The end result is not a universal assistant. It is a small agent framework that receives a task, sees a set of available tools, chooses actions, records observations, and stops when it has enough evidence. For a different class of tasks, the same loop can be started with a different task definition, action set, and evaluation.

I chose software debugging as the main domain because it is easy to evaluate with tests and it is relevant to developer tooling. To check that the mechanism was not only a debugging bot, I also added a research-style task where the agent reads local notes and produces a short brief. Finally, I extended the debugging setting into verified one-file repair, where the agent not only triages a failure but also edits one implementation file and verifies the fix.

The agent is built around a few simple objects: a task JSON file, a blueprint, a run state, a memory log, a chooser, and a small tool layer. The blueprint controls parameters such as how many files to read after a failure, whether to inspect files before or after running tests, and how many sources to read for research. The evaluator runs several blueprints on training tasks, selects the best one, and then evaluates it on held-out tasks.

The action chooser has two modes. In local mode, deterministic rules choose actions. In LLM mode, the model receives the task, current state, memory summary, and allowed actions, and returns one next action as JSON. If the LLM returns invalid JSON or an unsafe action, a local fallback and guard layer takes over. This became important because the model sometimes wanted to stop too early.

## 2. Architecture

The core loop is intentionally small:

```text
Task JSON -> build allowed actions -> choose next action -> execute tool -> update state/memory -> repeat -> produce artifact
```

The current actions are `run_command`, `read_file`, `write_file`, and `finish`. Different task types expose different useful actions, but the loop stays the same. Debugging tasks expose test commands and relevant files. Research tasks expose local text documents. Repair tasks expose the same debugging actions plus `write_file` actions for implementation files.

For code repair, I added a safer repair flow instead of letting the model freely edit the original project. Each run creates a runtime copy of the benchmark repository inside `.stem_runtime/`, so the original benchmark remains unchanged. When the agent chooses `write_file`, the system backs up the target file, asks the model for the full replacement contents, writes the replacement, reruns `python -m pytest -q`, and keeps the patch only if the test result improves. Otherwise, it restores the backup. This gave the repair step a clear safety boundary.

The repair action is also intentionally limited to one edited file. I made this choice to keep the verification and rollback logic reliable. Multi-file repair would be possible, but it creates more ways to overfit or break unrelated code, so I kept it as future work.

The agent produces task-specific artifacts. Debugging tasks produce triage reports with the failing command, likely files, and a useful output snippet. Research tasks produce a short brief. Repair tasks produce a repair report including the edited file, patch diff, repair command, and test result.

## 3. Experiments and Results

The benchmark is small and local. It contains debugging tasks, research tasks, and repair tasks. The training split is used to select the best blueprint. The held-out test split checks whether the selected blueprint transfers to unseen examples.

| Split | Tasks | Score |
|---|---|---:|
| Train | debugging, research, repair | 18 / 18 |
| Test | held-out debugging, research, repair | 14 / 14 |

The selected blueprint in the latest LLM repair run was `fast_finish`. This was interesting because the LLM-driven chooser changed the selected blueprint compared with earlier local runs. It showed that the model was not simply following the deterministic local policy.

The held-out repair task successfully fixed `list_utils.py`:

```diff
def first_item(items):
-    return items[1]
+    return items[0]
```

The repair was verified by rerunning tests, producing `1 passed`. The training repair task similarly fixed `math_utils.py` by changing subtraction into addition. In both cases, the agent worked through the same high-level process: reproduce failure, inspect files, choose one file to repair, apply a patch, rerun tests, and keep the fix only after verification.

The before/after comparison I care about is the change from triage-only behavior to verified repair behavior. Before the repair action existed, the agent could reproduce failures and identify likely files, but it could not improve the repository. After adding `write_file`, backup/rollback, and test verification, the repair tasks succeeded on both the training and held-out examples.

## 4. What Failed and What Surprised Me

The most useful failures were not model failures alone, but integration failures between the model and the tool loop.

First, the LLM was often too eager to finish. After reproducing a failure, it sometimes said the task was complete even though the task asked for repair. I added guards that prevent early stopping before the required progress is made. For example, research tasks cannot finish before reading enough sources, and repair tasks cannot finish before attempting repair.

Second, the LLM sometimes returned invalid JSON. Instead of treating this as a fatal error, I added a local fallback chooser. This made the system more robust while still allowing the model to drive normal decisions.

Third, my first runtime workspace design copied repositories into `outputs/runtime/`. My file scanner ignored `outputs/`, so the agent could run commands but could not see any files to read or repair. Moving runtime copies to `.stem_runtime/` fixed this and made the design cleaner.

Fourth, one repair generated the correct patch but was rolled back because the verification command was wrong. In this environment, `pytest -q` could fail with import issues, while `python -m pytest -q` worked reliably. Standardizing repair verification to `python -m pytest -q` fixed the problem. This failure was useful because it showed why rollback is important: the system should not keep a patch unless the verification step passes.

Finally, reusing one agent instance across multiple evaluation tasks polluted memory between tasks. I changed evaluation to create a fresh agent for each task. This made the results easier to interpret.

## 5. Limitations and Future Work

The current project is intentionally limited. The benchmark is small and synthetic. Repair is limited to one file. The research task reads local notes rather than browsing the web. The agent does not control a desktop or IDE. The evaluation uses simple expected-file and keyword checks, not a large benchmark suite.

I would extend the project in four directions with more time. First, I would add two-file repair with strict rules: only edit files already read, back up both files, and roll back if tests do not improve. Second, I would add setup and QA tasks, because they are different from pure code repair but still measurable. Third, I would make the evaluation harder by adding cases where the obvious file is not the correct file. Fourth, I would add optional browser or desktop tools only after the core loop remains stable.

The main lesson is that a useful stem agent is not just an LLM prompt. It needs a task format, allowed tools, memory, evaluation, guardrails, and verification. The most important design choice was to let the model choose actions while keeping the environment responsible for safety-critical steps such as backups, rollback, and test-based acceptance.
