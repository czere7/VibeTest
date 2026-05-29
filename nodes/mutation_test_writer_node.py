from typing import TYPE_CHECKING

from models import ModelWrapper
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
from exceptions import ContextWindowOverflowError

if TYPE_CHECKING:
    from AgentState import AgentState


def mutation_test_writer_node(agent_state: "AgentState") -> dict[str, str]:
    if agent_state.get('unrecoverable_error_for_current_class', False):
        return {}

    print(
        f"[mutation_test_writer_node] Adding mutation-focused tests "
        f"(iteration {agent_state.get('mutation_iterations', 0) + 1})."
    )
    prompt = _build_prompt(agent_state)

    try:
        response = ModelWrapper().invoke(prompt)
    except ContextWindowOverflowError:
        agent_state.set('unrecoverable_error_for_current_class', True)
        return {}

    updated_test_class = strip_markdown_code_fence(extract_response_content(response))

    if not updated_test_class:
        raise RuntimeError("Mutation test writer model returned an empty response.")

    print(f"[mutation_test_writer_node] Produced updated test class with {len(updated_test_class.splitlines())} line(s).")

    return {
        "test_class": updated_test_class,
        "active_validation_phase": "mutation",
        "repair_attempts": 0,
        "mutation_iterations": agent_state.get("mutation_iterations", 0) + 1,
    }


def _build_prompt(agent_state: "AgentState") -> str:
    test_class = agent_state.get("test_class", "").strip()
    mutation_feedback = agent_state.get("mutation_feedback", "").strip()

    if not test_class:
        raise RuntimeError("Cannot improve mutation score because AgentState['test_class'] is empty.")
    if not mutation_feedback:
        raise RuntimeError("Cannot improve mutation score because AgentState['mutation_feedback'] is empty.")

    class_under_test = get_current_class_under_test(agent_state)
    relevant_source_files = get_relevant_source_files(agent_state)
    nearby_test_examples = get_nearby_test_examples(agent_state)
    prompt_template = load_prompt("mutation_test_writer_prompt.md")

    return prompt_template.format(
        class_path=class_under_test.file_path,
        mutation_feedback=mutation_feedback,
        test_class=test_class,
        class_under_test=class_under_test.file_content,
        relevant_source_files=format_source_files_for_prompt(relevant_source_files),
        nearby_test_examples=format_test_examples_for_prompt(nearby_test_examples),
    )
