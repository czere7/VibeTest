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


def initial_test_write_node(agent_state: "AgentState") -> dict[str, str]:
    from models import common_generation_model

    class_under_test = get_current_class_under_test(agent_state)
    print(
        f"[initial_test_write_node] Generating initial test for "
        f"{agent_state.get('current_class_index', 0) + 1}/{len(agent_state.get('all_test_files', []))}: "
        f"{class_under_test.file_path}"
    )
    prompt = _build_prompt(agent_state)
    response = common_generation_model.invoke(prompt)
    test_class = strip_markdown_code_fence(extract_response_content(response))

    if not test_class:
        raise RuntimeError("Initial test writer model returned an empty response.")

    print(f"[initial_test_write_node] Generated initial test class with {len(test_class.splitlines())} line(s).")

    return {
        "test_class": test_class,
        "active_validation_phase": "coverage",
        "repair_attempts": 0,
    }


def _build_prompt(agent_state: "AgentState") -> str:
    class_under_test = get_current_class_under_test(agent_state)
    relevant_source_files = get_relevant_source_files(agent_state)
    nearby_test_examples = get_nearby_test_examples(agent_state)
    prompt_template = load_prompt("initial_test_write_prompt.md")

    return prompt_template.format(
        class_path=class_under_test.file_path,
        class_under_test=class_under_test.file_content,
        relevant_source_files=format_source_files_for_prompt(relevant_source_files),
        nearby_test_examples=format_test_examples_for_prompt(nearby_test_examples),
    )
