from pathlib import Path
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from utils import (
    calculate_mutation_score,
    find_pitest_xml_reports,
    get_float_config,
    get_current_class_under_test,
    get_java_fully_qualified_name,
    get_maven_module_directory,
    get_working_directory,
    run_pitest,
    summarize_pitest_mutations,
)

if TYPE_CHECKING:
    from AgentState import AgentState


def mutation_validator_node(agent_state: "AgentState") -> dict:
    project_dir = get_working_directory()
    threshold = get_float_config("MUTATION_IMPROVEMENT_THRESHOLD")
    previous_score = float(agent_state.get("mutation_current", 0.0))
    target_classes, target_tests, module_dir = _get_pitest_targets(agent_state, project_dir)
    print(
        f"[mutation_validator_node] Running PIT for class {target_classes} "
        f"with tests {target_tests} in module: {module_dir}"
    )

    pitest_result = run_pitest(str(module_dir), target_classes, target_tests)
    if not pitest_result["ok"]:
        mutation_feedback = _format_mutation_feedback(
            ok=False,
            previous_score=previous_score,
            current_score=previous_score,
            mutation_delta=0.0,
            threshold=threshold,
            metric_summary="",
            command_output=pitest_result["combined_result"],
        )
        print("[mutation_validator_node] PIT run failed; stored Maven output for diagnostics.")
        return {
            "mutation_previous": previous_score,
            "mutation_current": previous_score,
            "mutation_delta": 0.0,
            "mutation_improved_significantly": False,
            "mutation_feedback": mutation_feedback,
        }

    report_paths = find_pitest_xml_reports(module_dir)
    if not report_paths:
        raise RuntimeError(f"No PIT mutations.xml reports found under Maven module directory: {module_dir}")

    try:
        current_score = calculate_mutation_score(report_paths)
        metric_summary = summarize_pitest_mutations(report_paths, target_classes)
    except (ET.ParseError, OSError, ValueError) as error:
        raise RuntimeError(f"Failed to parse PIT mutation XML reports: {error}") from error

    mutation_delta = round(current_score - previous_score, 2)
    improved_significantly = mutation_delta >= threshold
    mutation_feedback = _format_mutation_feedback(
        ok=True,
        previous_score=previous_score,
        current_score=current_score,
        mutation_delta=mutation_delta,
        threshold=threshold,
        metric_summary=metric_summary,
        command_output=pitest_result["combined_result"],
    )

    print(
        f"[mutation_validator_node] Mutation score: {current_score:.2f}% "
        f"(previous {previous_score:.2f}%, delta {mutation_delta:.2f}%)."
    )

    return {
        "mutation_previous": previous_score,
        "mutation_current": current_score,
        "mutation_delta": mutation_delta,
        "mutation_improved_significantly": improved_significantly,
        "mutation_feedback": mutation_feedback,
    }


def _get_pitest_targets(agent_state: "AgentState", project_dir: Path) -> tuple[str, str, Path]:
    test_class = agent_state.get("test_class", "").strip()

    if not test_class:
        raise RuntimeError("Cannot run PIT because AgentState['test_class'] is empty.")

    class_under_test = get_current_class_under_test(agent_state)
    module_dir = get_maven_module_directory(class_under_test.file_path, project_dir)
    return (
        get_java_fully_qualified_name(class_under_test.file_content),
        get_java_fully_qualified_name(test_class),
        module_dir,
    )


def _format_mutation_feedback(
    ok: bool,
    previous_score: float,
    current_score: float,
    mutation_delta: float,
    threshold: float,
    metric_summary: str,
    command_output: str,
) -> str:
    if not ok:
        return (
            "Mutation validator result: PIT mutation report generation failed.\n"
            f"Mutation score previous: {previous_score:.2f}%\n"
            f"Mutation score current: {current_score:.2f}%\n"
            f"Mutation score delta: {mutation_delta:.2f}%\n"
            f"Significant improvement threshold: {threshold:.2f}%\n\n"
            "Maven output:\n"
            f"{command_output.strip()}"
        ).strip()

    return (
        "Mutation validator result: PIT mutation report generation succeeded.\n"
        f"Mutation score previous: {previous_score:.2f}%\n"
        f"Mutation score current: {current_score:.2f}%\n"
        f"Mutation score delta: {mutation_delta:.2f}%\n"
        f"Significant improvement threshold: {threshold:.2f}%\n\n"
        "Mutation details for the class under test:\n"
        f"{metric_summary.strip()}"
    ).strip()
