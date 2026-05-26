from typing import TYPE_CHECKING

from utils import (
    extract_response_content,
    format_source_files_for_prompt,
    format_test_examples_for_prompt,
    get_current_class_under_test,
    get_nearby_test_examples,
    get_relevant_source_files,
    load_prompt,
    strip_markdown_code_fence,
)

if TYPE_CHECKING:
    from AgentState import AgentState


def test_repair_node(agent_state: "AgentState") -> dict[str, str]:
    from models import common_generation_model

    print(
        f"[test_repair_node] Repairing test after compile failure "
        f"(attempt {agent_state.get('repair_attempts', 0) + 1})."
    )
    prompt = _build_prompt(agent_state)
    response = common_generation_model.invoke(prompt)
    repaired_test_class = strip_markdown_code_fence(extract_response_content(response))

    if not repaired_test_class:
        raise RuntimeError("Test repair model returned an empty response.")

    print(f"[test_repair_node] Produced repaired test class with {len(repaired_test_class.splitlines())} line(s).")

    return {
        "test_class": repaired_test_class,
        "repair_attempts": agent_state.get("repair_attempts", 0) + 1,
    }


def _build_prompt(agent_state: "AgentState") -> str:
    test_class = agent_state.get("test_class", "").strip()
    compiler_feedback = agent_state.get("compiler_feedback", "").strip()

    if not test_class:
        raise RuntimeError("Cannot repair tests because AgentState['test_class'] is empty.")
    if not compiler_feedback:
        raise RuntimeError("Cannot repair tests because AgentState['compiler_feedback'] is empty.")

    class_under_test = get_current_class_under_test(agent_state)
    relevant_source_files = get_relevant_source_files(agent_state)
    nearby_test_examples = get_nearby_test_examples(agent_state)
    prompt_template = load_prompt("test_repair_prompt.md")

    return prompt_template.format(
        class_path=class_under_test.file_path,
        compiler_feedback=compiler_feedback,
        test_class=test_class,
        last_compilable_test_class=_format_last_compilable_test_class(agent_state),
        class_under_test=class_under_test.file_content,
        relevant_source_files=format_source_files_for_prompt(relevant_source_files),
        nearby_test_examples=format_test_examples_for_prompt(nearby_test_examples),
    )


def _format_last_compilable_test_class(agent_state: "AgentState") -> str:
    last_compilable_test_class = agent_state.get("last_compilable_test_class", "").strip()
    if not last_compilable_test_class:
        return "No previous compilable version is available."

    return f"```java\n{last_compilable_test_class}\n```"
