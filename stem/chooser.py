import json

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


def choose_action_local(task: Task, actions, state: RunState, blueprint) -> ActionChoice:
    if task.task_type == "debugging":
        unread_files = [
            action for action in actions
            if action.kind == "read_file" and action.value not in state.files_read
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

        failure_words = ["traceback", "assert", "failed", "error"]
        saw_failure = any(
            any(word in observation.lower() for word in failure_words)
            for observation in state.observations
        )

        if saw_failure:
            if len(state.files_read) < blueprint.debugging_files_after_failure and unread_files:
                chosen = unread_files[0]
                return ActionChoice(
                    kind = chosen.kind,
                    value = chosen.value,
                    reason = "[local] After failure, inspect relevant files."
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


def choose_action_llm(task: Task, actions, state: RunState, blueprint, memory_summary: str) -> ActionChoice:
    action_text = "\n".join(
        [
            f"- kind={action.kind}, value={action.value}, label={action.label}"
            for action in actions
        ]
    )

    system_prompt = (
        "You are a careful agent. "
        "Choose exactly one next action from the allowed actions. "
        "Return JSON only with keys: kind, value, reason."
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

    if choice.kind == "finish":
        return choice

    if (choice.kind, choice.value) not in allowed_pairs:
        fallback = choose_action_local(task, actions, state, blueprint)
        fallback.reason = f"[fallback_not_allowed] {fallback.reason}"
        return fallback

    return choice