from pathlib import Path
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from utils import (
    calculate_branch_coverage_for_class,
    find_jacoco_xml_reports,
    get_float_config,
    get_current_class_under_test,
    get_java_fully_qualified_name,
    get_maven_module_directory,
    get_working_directory,
    run_jacoco,
    summarize_jacoco_coverage,
)

if TYPE_CHECKING:
    from AgentState import AgentState


def coverage_validator_node(agent_state: "AgentState") -> dict:
    project_dir = get_working_directory()
    threshold = get_float_config("COVERAGE_IMPROVEMENT_THRESHOLD")
    previous_coverage = float(agent_state.get("coverage_current", 0.0))
    target_class, module_dir = _get_coverage_target(agent_state, project_dir)
    print(f"[coverage_validator_node] Running JaCoCo for {target_class} in module: {module_dir}")

    jacoco_result = run_jacoco(str(module_dir))
    if not jacoco_result["ok"]:
        coverage_feedback = _format_coverage_feedback(
            ok=False,
            previous_coverage=previous_coverage,
            current_coverage=previous_coverage,
            coverage_delta=0.0,
            threshold=threshold,
            metric_summary="",
            command_output=jacoco_result["combined_result"],
        )
        print("[coverage_validator_node] JaCoCo run failed; stored Maven output for diagnostics.")
        return {
            "coverage_previous": previous_coverage,
            "coverage_current": previous_coverage,
            "coverage_delta": 0.0,
            "coverage_improved_significantly": False,
            "coverage_feedback": coverage_feedback,
        }

    report_paths = find_jacoco_xml_reports(module_dir)
    if not report_paths:
        raise RuntimeError(f"No JaCoCo XML reports found under Maven module directory: {module_dir}")

    try:
        current_coverage = calculate_branch_coverage_for_class(report_paths, target_class)
        metric_summary = summarize_jacoco_coverage(report_paths, target_class)
    except (ET.ParseError, OSError, ValueError) as error:
        raise RuntimeError(f"Failed to parse JaCoCo XML reports: {error}") from error

    coverage_delta = round(current_coverage - previous_coverage, 2)
    improved_significantly = coverage_delta >= threshold
    coverage_feedback = _format_coverage_feedback(
        ok=True,
        previous_coverage=previous_coverage,
        current_coverage=current_coverage,
        coverage_delta=coverage_delta,
        threshold=threshold,
        metric_summary=metric_summary,
        command_output=jacoco_result["combined_result"],
    )

    print(
        f"[coverage_validator_node] Branch coverage: {current_coverage:.2f}% "
        f"(previous {previous_coverage:.2f}%, delta {coverage_delta:.2f}%)."
    )

    return {
        "coverage_previous": previous_coverage,
        "coverage_current": current_coverage,
        "coverage_delta": coverage_delta,
        "coverage_improved_significantly": improved_significantly,
        "coverage_feedback": coverage_feedback,
    }


def _get_coverage_target(agent_state: "AgentState", project_dir: Path) -> tuple[str, Path]:
    class_under_test = get_current_class_under_test(agent_state)
    module_dir = get_maven_module_directory(class_under_test.file_path, project_dir)
    return get_java_fully_qualified_name(class_under_test.file_content), module_dir


def _format_coverage_feedback(
    ok: bool,
    previous_coverage: float,
    current_coverage: float,
    coverage_delta: float,
    threshold: float,
    metric_summary: str,
    command_output: str,
) -> str:
    if not ok:
        return (
            "Coverage validator result: JaCoCo report generation failed.\n"
            f"Branch coverage previous: {previous_coverage:.2f}%\n"
            f"Branch coverage current: {current_coverage:.2f}%\n"
            f"Branch coverage delta: {coverage_delta:.2f}%\n"
            f"Significant improvement threshold: {threshold:.2f}%\n\n"
            "Maven output:\n"
            f"{command_output.strip()}"
        ).strip()

    return (
        "Coverage validator result: JaCoCo report generation succeeded.\n"
        f"Branch coverage previous: {previous_coverage:.2f}%\n"
        f"Branch coverage current: {current_coverage:.2f}%\n"
        f"Branch coverage delta: {coverage_delta:.2f}%\n"
        f"Significant improvement threshold: {threshold:.2f}%\n\n"
        "Coverage details for the class under test:\n"
        f"{metric_summary.strip()}"
    ).strip()
