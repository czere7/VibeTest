import shutil
import re
import subprocess
import time, os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from datetime import datetime
import xml.etree.ElementTree as ET

from dotenv import dotenv_values

config = dotenv_values(".env")

PACKAGE_RE = re.compile(
    r'^\s*package\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;',
    re.MULTILINE,
)

CLASS_RE = re.compile(r'''
    ^[ \t]*
    (?:@(?!interface\b)[A-Za-z_$][\w$]*(?:\s*\([^)]*\))?\s*)*
    (?:
        (?:public|protected|private|abstract|final|static|strictfp|sealed|non-sealed)
        \s+
    )*
    (?:@interface|class|interface|enum|record)
    \s+
    ([A-Za-z_$][\w$]*)
    \b
''', re.MULTILINE | re.VERBOSE)

@dataclass
class SourceCodeFileData:
    file_path: str
    file_content: str

def is_concrete_class(java_code: str) -> bool:
    class_pattern = re.compile(
        r'\b(public|protected|private)\s*'
        r'(final\s+)?'
        r'(?!abstract\s+)'
        r'class\s+\w+',
        re.MULTILINE
    )
    if re.search(r'\b(enum|interface)\s+\w+', java_code):
        return False
    return bool(class_pattern.search(java_code))

def persist_current_class_index(index: int):
    tmp_file_location = str(config.get("CLASS_INDEX_TMP_FILE", "tmp.txt"))
    with open(tmp_file_location, "w", encoding="UTF-8") as file:
        file.write(str(index))

def retrieve_current_class_index() -> int:
    tmp_file_location = str(config.get("CLASS_INDEX_TMP_FILE", "tmp.txt"))
    if Path(tmp_file_location).is_file():
        with open(tmp_file_location, "r", encoding="UTF-8") as file:
            return int(file.read())
    return 0

def run_maven(project_dir: str):
    mvn_path = _get_maven_executable()
    result = subprocess.run(
        [mvn_path, "clean", "test"],
        cwd=project_dir,
        text=True,
        capture_output=True,
        shell=False
    )
    return {
        "ok": result.returncode == 0,
        "combined_result": result.stdout + "\n" + result.stderr,
    }

def _get_maven_executable() -> str:
    mvn_path = shutil.which("mvn")
    if mvn_path is None:
        raise RuntimeError("Maven executable 'mvn' was not found on PATH.")

    return mvn_path

def get_working_directory() -> Path:
    working_directory = config.get("WORKING_DIRECTORY")
    if not working_directory:
        raise RuntimeError("WORKING_DIRECTORY is not set in .env.")

    project_dir = Path(working_directory)
    if not project_dir.is_absolute():
        project_dir = Path.cwd() / project_dir

    if not project_dir.exists():
        raise RuntimeError(f"WORKING_DIRECTORY does not exist: {project_dir}")

    return project_dir

def get_maven_module_directory(source_file_path: str | Path, project_dir: str | Path | None = None) -> Path:
    project_path = Path(project_dir) if project_dir is not None else get_working_directory()
    project_path = project_path.resolve()
    current_path = Path(source_file_path).resolve()
    if current_path.is_file():
        current_path = current_path.parent

    try:
        current_path.relative_to(project_path)
    except ValueError as error:
        raise RuntimeError(f"Source file is not inside WORKING_DIRECTORY: {source_file_path}") from error

    while current_path != project_path.parent:
        if (current_path / "pom.xml").is_file():
            return current_path
        if current_path == project_path:
            break
        current_path = current_path.parent

    raise RuntimeError(f"No Maven module pom.xml found for source file: {source_file_path}")

def get_float_config(config_key: str) -> float:
    raw_value = config.get(config_key)
    if not raw_value:
        raise RuntimeError(f"{config_key} is not set in .env.")

    try:
        value = float(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{config_key} must be a number.") from error

    if value < 0:
        raise RuntimeError(f"{config_key} must be greater than or equal to 0.")

    return value

def get_int_config(config_key: str) -> int:
    raw_value = config.get(config_key)
    if not raw_value:
        raise RuntimeError(f"{config_key} is not set in .env.")

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{config_key} must be an integer.") from error

    if value < 0:
        raise RuntimeError(f"{config_key} must be greater than or equal to 0.")

    return value

def run_jacoco(project_dir: str):
    mvn_path = _get_maven_executable()
    result = subprocess.run(
        [mvn_path, "clean", "test", "jacoco:report"],
        cwd=project_dir,
        text=True,
        capture_output=True,
        shell=False
    )
    return {
        "ok": result.returncode == 0,
        "combined_result": result.stdout + "\n" + result.stderr,
    }

def run_pitest(project_dir: str, target_classes: str, target_tests: str):
    mvn_path = _get_maven_executable()
    result = subprocess.run(
        [
            mvn_path,
            "test-compile",
            "org.pitest:pitest-maven:mutationCoverage",
            f"-DtargetClasses={target_classes}",
            f"-DtargetTests={target_tests}",
            "-DoutputFormats=XML,HTML",
        ],
        cwd=project_dir,
        text=True,
        capture_output=True,
        shell=False
    )
    return {
        "ok": result.returncode == 0,
        "combined_result": result.stdout + "\n" + result.stderr,
    }

def find_jacoco_xml_reports(project_dir: str | Path) -> list[Path]:
    project_path = Path(project_dir)
    return sorted(project_path.rglob("target/site/jacoco/jacoco.xml"))

def find_pitest_xml_reports(project_dir: str | Path) -> list[Path]:
    project_path = Path(project_dir)
    reports = sorted(project_path.rglob("target/pit-reports/**/mutations.xml"))
    if not reports:
        return []

    latest_timestamp = max(report.stat().st_mtime for report in reports)
    return [report for report in reports if report.stat().st_mtime == latest_timestamp]

def calculate_branch_coverage(jacoco_report_paths: list[Path]) -> float:
    covered = 0
    missed = 0

    for report_path in jacoco_report_paths:
        root = ET.parse(report_path).getroot()
        for counter in root.findall("counter"):
            if counter.attrib.get("type") == "BRANCH":
                covered += int(counter.attrib.get("covered", "0"))
                missed += int(counter.attrib.get("missed", "0"))

    total = covered + missed
    if total == 0:
        return 0.0

    return round((covered / total) * 100, 2)

def calculate_branch_coverage_for_class(jacoco_report_paths: list[Path], target_class_name: str) -> float:
    covered = 0
    missed = 0
    jacoco_class_name = target_class_name.replace(".", "/")

    for report_path in jacoco_report_paths:
        root = ET.parse(report_path).getroot()
        class_element = _find_jacoco_class(root, jacoco_class_name)
        if class_element is None:
            continue

        for counter in class_element.findall("counter"):
            if counter.attrib.get("type") == "BRANCH":
                covered += int(counter.attrib.get("covered", "0"))
                missed += int(counter.attrib.get("missed", "0"))

    total = covered + missed
    if total == 0:
        return 0.0

    return round((covered / total) * 100, 2)

def summarize_jacoco_coverage(jacoco_report_paths: list[Path], target_class_name: str) -> str:
    jacoco_class_name = target_class_name.replace(".", "/")
    summary_lines = [f"Class under test: {target_class_name}"]

    for report_path in jacoco_report_paths:
        root = ET.parse(report_path).getroot()
        class_element = _find_jacoco_class(root, jacoco_class_name)
        if class_element is None:
            continue

        class_counter_summary = _format_jacoco_counters(class_element)
        if class_counter_summary:
            summary_lines.append(f"Class counters: {class_counter_summary}")

        method_lines = _summarize_jacoco_methods(class_element)
        if method_lines:
            summary_lines.append("Methods with missed branches or lines:")
            summary_lines.extend(method_lines)

        source_lines = _summarize_jacoco_source_lines(root, class_element)
        if source_lines:
            summary_lines.append("Source lines with missed branches or instructions:")
            summary_lines.extend(source_lines)

    if len(summary_lines) == 1:
        summary_lines.append("No JaCoCo class entry was found for the class under test.")

    return "\n".join(summary_lines)

def calculate_mutation_score(pitest_report_paths: list[Path]) -> float:
    killed = 0
    total = 0
    excluded_statuses = {"NON_VIABLE", "MEMORY_ERROR", "RUN_ERROR"}

    for report_path in pitest_report_paths:
        root = ET.parse(report_path).getroot()
        for mutation in root.findall("mutation"):
            status = mutation.attrib.get("status", "").upper()
            if status in excluded_statuses:
                continue
            if status == "KILLED":
                killed += 1
            total += 1

    if total == 0:
        return 0.0

    return round((killed / total) * 100, 2)

def summarize_pitest_mutations(pitest_report_paths: list[Path], target_class_name: str) -> str:
    status_counts: dict[str, int] = {}
    actionable_mutations = []

    for report_path in pitest_report_paths:
        root = ET.parse(report_path).getroot()
        for mutation in root.findall("mutation"):
            mutated_class = _child_text_no_namespace(mutation, "mutatedClass")
            if mutated_class and mutated_class != target_class_name:
                continue

            status = mutation.attrib.get("status", "UNKNOWN").upper()
            status_counts[status] = status_counts.get(status, 0) + 1

            if status in {"SURVIVED", "NO_COVERAGE", "TIMED_OUT"}:
                actionable_mutations.append(_format_pitest_mutation(mutation, status))

    summary_lines = [f"Class under test: {target_class_name}"]
    if status_counts:
        counts = ", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items()))
        summary_lines.append(f"Mutation status counts: {counts}")
    else:
        summary_lines.append("No PIT mutation entries were found for the class under test.")

    if actionable_mutations:
        summary_lines.append("Surviving or uncovered mutations to target:")
        summary_lines.extend(actionable_mutations[:20])
        if len(actionable_mutations) > 20:
            summary_lines.append(f"... {len(actionable_mutations) - 20} additional actionable mutations omitted.")

    return "\n".join(summary_lines)

def _find_jacoco_class(root: ET.Element, jacoco_class_name: str) -> ET.Element | None:
    for class_element in root.iter("class"):
        if class_element.attrib.get("name") == jacoco_class_name:
            return class_element
    return None

def _format_jacoco_counters(element: ET.Element) -> str:
    counters = []
    for counter in element.findall("counter"):
        counter_type = counter.attrib.get("type", "")
        missed = int(counter.attrib.get("missed", "0"))
        covered = int(counter.attrib.get("covered", "0"))
        total = missed + covered
        percent = 0.0 if total == 0 else round((covered / total) * 100, 2)
        counters.append(f"{counter_type} {percent:.2f}% ({covered} covered, {missed} missed)")
    return "; ".join(counters)

def _summarize_jacoco_methods(class_element: ET.Element) -> list[str]:
    method_summaries = []
    for method in class_element.findall("method"):
        method_name = method.attrib.get("name", "<unknown>")
        line_number = method.attrib.get("line", "?")
        missed_parts = []
        for counter in method.findall("counter"):
            counter_type = counter.attrib.get("type", "")
            missed = int(counter.attrib.get("missed", "0"))
            if missed > 0 and counter_type in {"BRANCH", "LINE", "INSTRUCTION"}:
                covered = int(counter.attrib.get("covered", "0"))
                missed_parts.append(f"{counter_type}: {missed} missed, {covered} covered")
        if missed_parts:
            method_summaries.append(f"- {method_name} at line {line_number}: " + "; ".join(missed_parts))
    return method_summaries

def _summarize_jacoco_source_lines(root: ET.Element, class_element: ET.Element) -> list[str]:
    source_filename = class_element.attrib.get("sourcefilename")
    if not source_filename:
        return []

    sourcefile = None
    for candidate in root.iter("sourcefile"):
        if candidate.attrib.get("name") == source_filename:
            sourcefile = candidate
            break

    if sourcefile is None:
        return []

    line_summaries = []
    for line in sourcefile.findall("line"):
        missed_branches = int(line.attrib.get("mb", "0"))
        covered_branches = int(line.attrib.get("cb", "0"))
        missed_instructions = int(line.attrib.get("mi", "0"))
        if missed_branches > 0 or missed_instructions > 0:
            line_summaries.append(
                f"- line {line.attrib.get('nr')}: "
                f"branches {covered_branches} covered/{missed_branches} missed, "
                f"instructions missed {missed_instructions}"
            )
    return line_summaries[:30]

def _format_pitest_mutation(mutation: ET.Element, status: str) -> str:
    mutated_method = _child_text_no_namespace(mutation, "mutatedMethod") or "<unknown>"
    line_number = _child_text_no_namespace(mutation, "lineNumber") or "?"
    mutator = _child_text_no_namespace(mutation, "mutator") or "<unknown mutator>"
    description = _child_text_no_namespace(mutation, "description") or "No description provided."
    return f"- {status} in {mutated_method} at line {line_number}: {mutator}; {description}"

def _child_text_no_namespace(parent: ET.Element, child_name: str) -> str:
    child = parent.find(child_name)
    return "" if child is None or child.text is None else child.text.strip()

def get_java_entity_name(java_code: str) -> str:
    class_match = CLASS_RE.search(java_code)
    if class_match is None:
        raise RuntimeError("Java code does not contain a class, interface, enum, or record declaration.")

    return class_match.group(1)

def get_java_package_name(java_code: str) -> str:
    package_match = PACKAGE_RE.search(java_code)
    if package_match is None:
        return ""

    return package_match.group(1)

def get_java_fully_qualified_name(java_code: str) -> str:
    entity_name = get_java_entity_name(java_code)
    package_name = get_java_package_name(java_code)
    if not package_name:
        return entity_name

    return f"{package_name}.{entity_name}"

def ensure_file(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path

def load_prompt(prompt_file_name: str) -> str:
    prompt_path = Path(__file__).resolve().parent / "prompts" / prompt_file_name
    return prompt_path.read_text(encoding="utf-8")

def format_source_files_for_prompt(source_files: list[SourceCodeFileData]) -> str:
    if not source_files:
        return "No directly referenced source files were found."

    formatted_files = []
    for index, source_file in enumerate(source_files, start=1):
        formatted_files.append(
            f"### Relevant Source File {index}\n\n"
            f"Path: `{source_file.file_path}`\n\n"
            f"```java\n{source_file.file_content}\n```"
        )

    return "\n\n".join(formatted_files)

def get_nearby_test_examples(agent_state: Mapping[str, Any], limit: int = 2) -> list[SourceCodeFileData]:
    class_under_test = get_current_class_under_test(agent_state)
    project_dir = get_working_directory()
    module_dir = get_maven_module_directory(class_under_test.file_path, project_dir)
    test_roots = [module_dir / "src" / "test" / "java", module_dir / "src" / "test"]
    package_name = get_java_package_name(class_under_test.file_content)
    package_path = Path(*package_name.split(".")) if package_name else Path()
    excluded_path = Path(agent_state.get("test_file_path", "")).resolve() if agent_state.get("test_file_path") else None

    ranked_candidates: list[Path] = []
    for test_root in test_roots:
        if not test_root.is_dir():
            continue

        package_dir = test_root / package_path
        if package_dir.is_dir():
            ranked_candidates.extend(sorted(package_dir.glob("*Test.java")))

        ranked_candidates.extend(sorted(test_root.rglob("*Test.java")))

    examples = []
    seen_paths = set()
    for candidate in ranked_candidates:
        resolved_candidate = candidate.resolve()
        if resolved_candidate in seen_paths:
            continue
        if excluded_path is not None and resolved_candidate == excluded_path:
            continue
        seen_paths.add(resolved_candidate)

        try:
            content = candidate.read_text(encoding="utf-8")
        except OSError:
            continue

        examples.append(SourceCodeFileData(str(candidate), content))
        if len(examples) >= limit:
            break

    return examples

def format_test_examples_for_prompt(test_examples: list[SourceCodeFileData]) -> str:
    if not test_examples:
        return "No nearby existing test examples were found in this Maven module."

    formatted_examples = []
    for index, test_example in enumerate(test_examples, start=1):
        formatted_examples.append(
            f"### Existing Test Example {index}\n\n"
            f"Path: `{test_example.file_path}`\n\n"
            f"```java\n{_truncate_prompt_content(test_example.file_content, 12000)}\n```"
        )

    return "\n\n".join(formatted_examples)

def _truncate_prompt_content(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content

    return content[:max_chars].rstrip() + "\n// ... truncated for prompt length"

def extract_response_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(_content_part_to_text(part) for part in content).strip()
    return str(content).strip()

def strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped

def get_relevant_source_files(agent_state: Mapping[str, Any]) -> list[SourceCodeFileData]:
    all_files = agent_state["all_files"]
    class_under_test = get_current_class_under_test(agent_state)
    relevant_files = []

    for source_file in all_files:
        if source_file.file_path == class_under_test.file_path:
            continue

        class_match = CLASS_RE.search(source_file.file_content)
        if class_match and class_match.group(1) in class_under_test.file_content:
            relevant_files.append(source_file)

    return relevant_files

def get_current_class_under_test(agent_state: Mapping[str, Any]) -> SourceCodeFileData:
    all_test_files = agent_state["all_test_files"]
    current_class_index = agent_state["current_class_index"]
    if current_class_index < 0 or current_class_index >= len(all_test_files):
        raise IndexError(f"current_class_index out of range: {current_class_index}")

    return all_test_files[current_class_index]

def initial_metric_state() -> dict[str, Any]:
    return {
        "test_class": "",
        "compiler_success": False,
        "compiler_feedback": "",
        "test_file_path": "",
        "last_compilable_test_class": "",
        "last_compilable_test_file_path": "",
        "coverage_previous": 0.0,
        "coverage_current": 0.0,
        "coverage_delta": 0.0,
        "coverage_improved_significantly": False,
        "coverage_feedback": "",
        "mutation_previous": 0.0,
        "mutation_current": 0.0,
        "mutation_delta": 0.0,
        "mutation_improved_significantly": False,
        "mutation_feedback": "",
        "active_validation_phase": "coverage",
        "repair_attempts": 0,
        "coverage_iterations": 0,
        "mutation_iterations": 0,
    }

def reset_state_for_current_class() -> dict[str, Any]:
    return initial_metric_state()

def advance_to_next_class(agent_state: Mapping[str, Any]) -> dict[str, Any]:
    next_index = agent_state["current_class_index"] + 1
    return {
        "current_class_index": next_index,
        **reset_state_for_current_class(),
    }

def _content_part_to_text(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        return str(part.get("text", ""))
    return str(part)

def log_litellm_response_error(litellm_response):
    full_message = f'{datetime.now} message'

    filename_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join('log_miscelaneous', f'{filename_date}.log')

    with open(filename, 'a+', encoding='utf-8-sig') as f:
        f.write(full_message)

def log_serious_error(message):
    full_message = f'{datetime.now} message'

    filename_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join('log_serious', f'{filename_date}.log')

    with open(filename, 'a+', encoding='utf-8-sig') as f:
        f.write(full_message)