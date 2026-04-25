import json
from pathlib import Path

from stem.llm import ask_model
from stem.types import ActionChoice, RunState, Task


def clean_json(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


def saw_failure(state: RunState) -> bool:
    failure_words = ["traceback", "assert", "failed", "error"]

    return any(
        any(word in observation.lower() for word in failure_words)
        for observation in state.observations
    )


def choose_action_local(task: Task, actions, state: RunState, blueprint) -> ActionChoice:
    if task.task_type == "debugging":
        repair_goal = bool(task.goal.get("repair_code"))

        unread_files = [
            action for action in actions
            if action.kind == "read_file" and action.value not in state.files_read
        ]

        write_actions = [
            action for action in actions
            if action.kind == "write_file" and action.value not in state.edited_files
        ]

        if not state.commands_tried:
            if blueprint.debugging_start_mode == "read_first" and unread_files:
                chosen = unread_files[0]
                return ActionChoice(
                    kind = chosen.kind,
                    value = chosen.value,
                    reason = "[local] This blueprint inspects a file before running tests."
                )

            for action in actions:
                if action.kind == "run_command" and action.value == "pytest -q":
                    return ActionChoice(
                        kind = action.kind,
                        value = action.value,
                        reason = "[local] Start by running the main test command."
                    )

        if saw_failure(state):
            if len(state.files_read) < blueprint.debugging_files_after_failure and unread_files:
                chosen = unread_files[0]
                return ActionChoice(
                    kind = chosen.kind,
                    value = chosen.value,
                    reason = "[local] After failure, inspect relevant files."
                )

            if repair_goal and not state.repair_attempted and write_actions:
                preferred_targets = [
                    path for path in state.files_read
                    if path.endswith(".py") and "test" not in Path(path).name.lower()
                ]

                for target in preferred_targets:
                    for action in write_actions:
                        if action.value == target:
                            return ActionChoice(
                                kind = action.kind,
                                value = action.value,
                                reason = "[local] Attempt one-file repair in the likely implementation file."
                            )

                chosen = write_actions[0]
                return ActionChoice(
                    kind = chosen.kind,
                    value = chosen.value,
                    reason = "[local] Attempt one-file repair."
                )

            return ActionChoice(
                kind = "finish",
                value = "",
                reason = "[local] Enough evidence was collected."
            )

        if unread_files:
            chosen = unread_files[0]
            return ActionChoice(
                kind = chosen.kind,
                value = chosen.value,
                reason = "[local] Inspect a file because no strong evidence was found yet."
            )

        return ActionChoice(
            kind = "finish",
            value = "",
            reason = "[local] No better next step is available."
        )

    if task.task_type == "research":
        unread_files = [
            action for action in actions
            if action.kind == "read_file" and action.value not in state.files_read
        ]

        if len(state.files_read) < blueprint.research_min_files and unread_files:
            chosen = unread_files[0]
            return ActionChoice(
                kind = chosen.kind,
                value = chosen.value,
                reason = "[local] Read another source before finishing."
            )

        return ActionChoice(
            kind = "finish",
            value = "",
            reason = "[local] Enough sources were read."
        )

    first = actions[0]
    return ActionChoice(
        kind = first.kind,
        value = first.value,
        reason = "[local] Fallback action."
    )


def guard_choice(task: Task, actions, state: RunState, blueprint, choice: ActionChoice) -> ActionChoice:
    """
    Safety layer around the LLM decision.

    The LLM may be too eager to finish or keep running commands.
    This guard forces minimum progress before accepting finish, and
    stops after one repair attempt.
    """

    if task.task_type == "research":
        if choice.kind == "finish" and len(state.files_read) < blueprint.research_min_files:
            fallback = choose_action_local(task, actions, state, blueprint)
            fallback.reason = f"[guard_research_finish_too_early] {fallback.reason}"
            return fallback

    if task.task_type == "debugging":
        repair_goal = bool(task.goal.get("repair_code"))
        failure_seen = saw_failure(state)

        # One-file repair rule: after one repair attempt, stop.
        if repair_goal and state.repair_attempted:
            return ActionChoice(
                kind = "finish",
                value = "",
                reason = "[guard_one_file_repair_done] One-file repair was already attempted, so finish."
            )

        # For repair tasks, do not keep running commands after seeing a failure.
        # First inspect files, then repair.
        if repair_goal and failure_seen and choice.kind == "run_command":
            fallback = choose_action_local(task, actions, state, blueprint)
            fallback.reason = f"[guard_read_or_repair_before_more_commands] {fallback.reason}"
            return fallback

        # For repair tasks, do not finish before repair is attempted.
        if repair_goal and choice.kind == "finish":
            fallback = choose_action_local(task, actions, state, blueprint)
            fallback.reason = f"[guard_repair_not_attempted] {fallback.reason}"
            return fallback

        # For non-repair debugging, do not finish immediately after failure
        # without reading at least one file.
        if not repair_goal and choice.kind == "finish":
            if failure_seen and len(state.files_read) == 0:
                fallback = choose_action_local(task, actions, state, blueprint)
                fallback.reason = f"[guard_no_file_read_after_failure] {fallback.reason}"
                return fallback

        # Do not allow repair before failure is reproduced.
        if choice.kind == "write_file":
            if not repair_goal:
                fallback = choose_action_local(task, actions, state, blueprint)
                fallback.reason = f"[guard_write_not_requested] {fallback.reason}"
                return fallback

            if not failure_seen:
                fallback = choose_action_local(task, actions, state, blueprint)
                fallback.reason = f"[guard_write_before_failure] {fallback.reason}"
                return fallback

            if choice.value not in state.files_read:
                fallback = choose_action_local(task, actions, state, blueprint)
                fallback.reason = f"[guard_write_before_reading_target] {fallback.reason}"
                return fallback

    return choice


def choose_action_llm(task: Task, actions, state: RunState, blueprint, memory_summary: str) -> ActionChoice:
    action_text = "\n".join(
        [
            f"- kind={action.kind}, value={action.value}, label={action.label}"
            for action in actions
        ]
    )

    system_prompt = (
        "You are a careful task-solving agent. "
        "Choose exactly one next action from the allowed actions. "
        "Return JSON only with keys: kind, value, reason. "
        "Do not finish until the task goal is actually satisfied. "
        "For research tasks, do not finish before reading the required number of sources. "
        "For code repair tasks, do not finish after only reproducing the failure. "
        "For code repair tasks, after reproducing the failure and reading the likely implementation file, "
        "choose a write_file action to attempt a one-file repair."
    )

    user_prompt = f"""
Task type: {task.task_type}
Task title: {task.title}
Issue: {task.issue}
Goal: {json.dumps(task.goal)}

Blueprint:
- name: {blueprint.name}
- debugging_start_mode: {getattr(blueprint, "debugging_start_mode", "")}
- debugging_files_after_failure: {getattr(blueprint, "debugging_files_after_failure", "")}
- research_min_files: {getattr(blueprint, "research_min_files", "")}

Current state:
- commands_tried: {state.commands_tried}
- files_read: {state.files_read}
- edited_files: {state.edited_files}
- repair_attempted: {state.repair_attempted}
- repair_success: {state.repair_success}
- finish_requested: {state.finish_requested}

Recent memory:
{memory_summary}

Allowed actions:
{action_text}

Return only JSON.
"""

    raw = ask_model(
        system_prompt = system_prompt,
        user_prompt = user_prompt,
        model = blueprint.model
    )

    try:
        parsed = json.loads(clean_json(raw))
        choice = ActionChoice(**parsed)
        choice.reason = f"[llm] {choice.reason}"
    except Exception:
        fallback = choose_action_local(task, actions, state, blueprint)
        fallback.reason = f"[fallback_invalid_json] {fallback.reason}"
        return fallback

    allowed_pairs = {(action.kind, action.value) for action in actions}

    if choice.kind != "finish" and (choice.kind, choice.value) not in allowed_pairs:
        fallback = choose_action_local(task, actions, state, blueprint)
        fallback.reason = f"[fallback_not_allowed] {fallback.reason}"
        return fallback

    return guard_choice(task, actions, state, blueprint, choice)