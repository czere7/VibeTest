from pathlib import Path
from typing import TYPE_CHECKING

from utils import ensure_file, get_current_class_under_test, get_java_entity_name, get_working_directory, run_maven

if TYPE_CHECKING:
    from AgentState import AgentState


def compiler_node(agent_state: "AgentState") -> dict:
    print(f"Compiler Node. unrecoverable_error_for_current_class:{agent_state.get('unrecoverable_error_for_current_class', 'default')}")
    if agent_state.get('unrecoverable_error_for_current_class', False):
        return {}
    
    test_class = agent_state.get("test_class", "").strip()
    if not test_class:
        raise RuntimeError("Cannot compile tests because AgentState['test_class'] is empty.")

    project_dir = get_working_directory()
    class_under_test = get_current_class_under_test(agent_state)
    source_file_path = Path(class_under_test.file_path)
    print(f"[compiler_node] Writing and compiling generated test for: {source_file_path}")
    test_file_path = _write_test_class(project_dir, source_file_path, test_class)
    print(f"[compiler_node] Test file written to: {test_file_path}")
    maven_result = run_maven(str(project_dir))

    compiler_feedback = _format_compiler_feedback(
        ok=maven_result["ok"],
        test_file_path=test_file_path,
        combined_result=maven_result["combined_result"],
    )

    state_update = {
        "compiler_success": maven_result["ok"],
        "compiler_feedback": compiler_feedback,
        "test_file_path": str(test_file_path),
        "messages": [
            {
                "role": "user",
                "content": compiler_feedback,
            }
        ],
    }
    if maven_result["ok"]:
        state_update["last_compilable_test_class"] = test_class
        state_update["last_compilable_test_file_path"] = str(test_file_path)
        print("[compiler_node] Maven test run passed. Stored this test as last known compilable version.")
    else:
        print("[compiler_node] Maven test run failed. Routing will attempt repair if attempts remain.")

    return state_update


def _write_test_class(project_dir: Path, source_file_path: Path, test_class: str) -> Path:
    relative_source_path = _relative_source_path(project_dir, source_file_path)
    relative_test_path = _source_path_to_test_path(relative_source_path, test_class)
    test_file_path = project_dir / relative_test_path

    ensure_file(test_file_path)
    test_file_path.write_text(test_class + "\n", encoding="utf-8")
    return test_file_path


def _relative_source_path(project_dir: Path, source_file_path: Path) -> Path:
    project_dir = project_dir.resolve()
    source_file_path = source_file_path.resolve()

    try:
        return source_file_path.relative_to(project_dir)
    except ValueError as error:
        raise RuntimeError(f"Source file is not inside WORKING_DIRECTORY: {source_file_path}") from error


def _source_path_to_test_path(relative_source_path: Path, test_class: str) -> Path:
    parts = list(relative_source_path.parts)
    try:
        src_index = parts.index("src")
        main_index = src_index + 1
    except ValueError as error:
        raise RuntimeError(f"Source file path does not contain a src/main segment: {relative_source_path}") from error

    if main_index >= len(parts) or parts[main_index] != "main":
        raise RuntimeError(f"Source file path does not contain a src/main segment: {relative_source_path}")

    parts[main_index] = "test"
    test_class_name = get_java_entity_name(test_class)
    parts[-1] = f"{test_class_name}.java"
    return Path(*parts)


def _format_compiler_feedback(ok: bool, test_file_path: Path, combined_result: str) -> str:
    status = "passed" if ok else "failed"
    output = combined_result.strip() if ok else _compact_maven_failure(combined_result)
    return (
        f"Compiler node result: Maven test compilation {status}.\n"
        f"Generated test file: {test_file_path}\n\n"
        "Relevant Maven output:\n"
        f"{output}"
    ).strip()


def _compact_maven_failure(combined_result: str) -> str:
    lines = combined_result.splitlines()
    build_failure_index = _find_first_line_index(lines, ("BUILD FAILURE",))
    if build_failure_index is None:
        compacted = "\n".join(lines[-120:])
    else:
        start_index = max(0, build_failure_index - 120)
        compacted = "\n".join(lines[start_index : build_failure_index + 1])

    max_chars = 12000
    if len(compacted) > max_chars:
        return "... truncated Maven failure output\n" + compacted[-max_chars:].lstrip()

    return compacted.strip()


def _find_first_line_index(lines: list[str], markers: tuple[str, ...]) -> int | None:
    for index, line in enumerate(lines):
        if any(marker in line for marker in markers):
            return index
    return None
