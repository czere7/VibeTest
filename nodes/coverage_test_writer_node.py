from typing import TYPE_CHECKING

from utils import (
    extract_response_content,
    format_source_files_for_prompt,
    format_test_examples_for_prompt,
    get_current_class_under_test,
    get_nearby_test_examples,
    get_relevant_source_files,
    load_prompt,
    retry_model_invocation,
    strip_markdown_code_fence,
)

if TYPE_CHECKING:
    from AgentState import AgentState


def coverage_test_writer_node(agent_state: "AgentState") -> dict[str, str]:
    from models import common_generation_model

    print(
        f"[coverage_test_writer_node] Adding coverage-focused tests "
        f"(iteration {agent_state.get('coverage_iterations', 0) + 1})."
    )
    prompt = _build_prompt(agent_state)
    response = retry_model_invocation(lambda: common_generation_model.invoke(prompt))
    updated_test_class = strip_markdown_code_fence(extract_response_content(response))

    if not updated_test_class:
        raise RuntimeError("Coverage test writer model returned an empty response.")

    print(f"[coverage_test_writer_node] Produced updated test class with {len(updated_test_class.splitlines())} line(s).")

    return {
        "test_class": updated_test_class,
        "active_validation_phase": "coverage",
        "repair_attempts": 0,
        "coverage_iterations": agent_state.get("coverage_iterations", 0) + 1,
    }


def _build_prompt(agent_state: "AgentState") -> str:
    test_class = agent_state.get("test_class", "").strip()
    coverage_feedback = agent_state.get("coverage_feedback", "").strip()

    if not test_class:
        raise RuntimeError("Cannot improve coverage because AgentState['test_class'] is empty.")
    if not coverage_feedback:
        raise RuntimeError("Cannot improve coverage because AgentState['coverage_feedback'] is empty.")

    class_under_test = get_current_class_under_test(agent_state)
    relevant_source_files = get_relevant_source_files(agent_state)
    nearby_test_examples = get_nearby_test_examples(agent_state)
    prompt_template = load_prompt("coverage_test_writer_prompt.md")

    return prompt_template.format(
        class_path=class_under_test.file_path,
        coverage_feedback=coverage_feedback,
        test_class=test_class,
        class_under_test=class_under_test.file_content,
        relevant_source_files=format_source_files_for_prompt(relevant_source_files),
        nearby_test_examples=format_test_examples_for_prompt(nearby_test_examples),
    )
