from pathlib import Path
import re
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from utils import get_working_directory

if TYPE_CHECKING:
    from AgentState import AgentState


DEPENDENCIES = [
    {
        "groupId": "junit",
        "artifactId": "junit",
        "version": "4.13.2",
        "scope": "test",
    },
    {
        "groupId": "org.mockito",
        "artifactId": "mockito-core",
        "version": "5.12.0",
        "scope": "test",
    },
]

SLF4J_FALLBACK_BINDING = {
    "groupId": "org.slf4j",
    "artifactId": "slf4j-nop",
    "version": "1.5.8",
    "scope": "test",
}

SLF4J_BINDINGS = {
    ("ch.qos.logback", "logback-classic"),
    ("org.apache.logging.log4j", "log4j-slf4j-impl"),
    ("org.slf4j", "slf4j-jdk14"),
    ("org.slf4j", "slf4j-log4j12"),
    ("org.slf4j", "slf4j-nop"),
    ("org.slf4j", "slf4j-reload4j"),
    ("org.slf4j", "slf4j-simple"),
}

PLUGINS = [
    {
        "groupId": "org.jacoco",
        "artifactId": "jacoco-maven-plugin",
        "version": "0.8.12",
        "executions": [
            {
                "id": "prepare-agent",
                "goals": ["prepare-agent"],
            },
            {
                "id": "report",
                "phase": "test",
                "goals": ["report"],
            },
        ],
    },
    {
        "groupId": "org.pitest",
        "artifactId": "pitest-maven",
        "version": "1.15.8",
    },
]

SUREFIRE_PLUGIN = {
    "groupId": "org.apache.maven.plugins",
    "artifactId": "maven-surefire-plugin",
    "version": "3.2.5",
    "junit4Provider": {
        "groupId": "org.apache.maven.surefire",
        "artifactId": "surefire-junit4",
        "version": "3.2.5",
    },
    "testngProvider": {
        "groupId": "org.apache.maven.surefire",
        "artifactId": "surefire-testng",
        "version": "3.2.5",
    },
    "includes": [
        "**/Test*.java",
        "**/*Test.java",
        "**/*TestCase.java",
    ],
}


def dependency_resolver_node(agent_state: "AgentState") -> dict:
    project_dir = get_working_directory()
    print(f"[dependency_resolver_node] Resolving Maven test dependencies under: {project_dir}")
    pom_paths = _find_pom_files(project_dir)
    if not pom_paths:
        raise RuntimeError(f"No pom.xml files found under WORKING_DIRECTORY: {project_dir}")

    errors = []
    for pom_path in pom_paths:
        try:
            _update_pom(pom_path)
        except (ET.ParseError, OSError, ValueError) as error:
            errors.append(f"{pom_path}: {error}")

    if errors:
        raise RuntimeError("Failed to update one or more pom.xml files:\n" + "\n".join(errors))

    print(f"[dependency_resolver_node] Updated dependency/plugin configuration in {len(pom_paths)} pom.xml file(s).")

    return {}


def _find_pom_files(project_dir: Path) -> list[Path]:
    return sorted(
        pom_path
        for pom_path in project_dir.rglob("pom.xml")
        if "target" not in pom_path.relative_to(project_dir).parts
    )


def _update_pom(pom_path: Path) -> None:
    tree = ET.parse(pom_path)
    root = tree.getroot()
    namespace = _namespace(root)

    if namespace:
        ET.register_namespace("", namespace)

    dependencies_element = _get_or_create_child(root, "dependencies", namespace)
    for dependency in DEPENDENCIES:
        _ensure_dependency(dependencies_element, dependency, namespace)
    _ensure_slf4j_fallback_binding(pom_path, dependencies_element, namespace)

    build_element = _get_or_create_child(root, "build", namespace)
    plugins_element = _get_or_create_child(build_element, "plugins", namespace)
    for plugin in PLUGINS:
        _ensure_plugin(plugins_element, plugin, namespace)
    _ensure_surefire_plugin(plugins_element, namespace)

    ET.indent(tree, space="    ")
    tree.write(pom_path, encoding="utf-8", xml_declaration=True)


def _ensure_dependency(parent: ET.Element, dependency: dict[str, str], namespace: str | None) -> None:
    existing_dependency = _find_artifact(parent, "dependency", dependency["groupId"], dependency["artifactId"], namespace)
    if existing_dependency is None:
        existing_dependency = ET.SubElement(parent, _tag("dependency", namespace))

    for key in ("groupId", "artifactId", "version", "scope"):
        _set_child_text_if_missing(existing_dependency, key, dependency[key], namespace)


def _ensure_slf4j_fallback_binding(
    pom_path: Path,
    dependencies_element: ET.Element,
    namespace: str | None,
) -> None:
    existing_fallback = _find_artifact(
        dependencies_element,
        "dependency",
        SLF4J_FALLBACK_BINDING["groupId"],
        SLF4J_FALLBACK_BINDING["artifactId"],
        namespace,
    )
    needs_fallback = (
        _module_has_java_sources(pom_path)
        and not _module_declares_other_slf4j_binding(dependencies_element, namespace)
        and not _module_provides_static_logger_binder(pom_path)
    )

    if needs_fallback:
        _ensure_dependency(dependencies_element, SLF4J_FALLBACK_BINDING, namespace)
    elif existing_fallback is not None:
        dependencies_element.remove(existing_fallback)


def _module_declares_other_slf4j_binding(parent: ET.Element, namespace: str | None) -> bool:
    for dependency in _children(parent, "dependency", namespace):
        coordinates = (
            _child_text(dependency, "groupId", namespace),
            _child_text(dependency, "artifactId", namespace),
        )
        if coordinates in SLF4J_BINDINGS and coordinates != (
            SLF4J_FALLBACK_BINDING["groupId"],
            SLF4J_FALLBACK_BINDING["artifactId"],
        ):
            return True
    return False


def _module_provides_static_logger_binder(pom_path: Path) -> bool:
    module_dir = pom_path.parent
    source_roots = [
        module_dir / "src" / "main",
        module_dir / "src" / "test",
    ]
    return any(
        source_root.exists() and any(source_root.rglob("StaticLoggerBinder.java"))
        for source_root in source_roots
    )


def _module_has_java_sources(pom_path: Path) -> bool:
    module_dir = pom_path.parent
    source_roots = [
        module_dir / "src" / "main" / "java",
        module_dir / "src" / "test" / "java",
    ]
    return any(source_root.exists() and any(source_root.rglob("*.java")) for source_root in source_roots)


def _ensure_plugin(parent: ET.Element, plugin: dict, namespace: str | None) -> None:
    existing_plugin = _find_artifact(parent, "plugin", plugin["groupId"], plugin["artifactId"], namespace)
    if existing_plugin is None:
        existing_plugin = ET.SubElement(parent, _tag("plugin", namespace))

    for key in ("groupId", "artifactId", "version"):
        _set_child_text_if_missing(existing_plugin, key, plugin[key], namespace)

    if "executions" in plugin:
        executions_element = _get_or_create_child(existing_plugin, "executions", namespace)
        for execution in plugin["executions"]:
            _ensure_execution(executions_element, execution, namespace)


def _ensure_surefire_plugin(parent: ET.Element, namespace: str | None) -> None:
    existing_plugin = _find_plugin(
        parent,
        SUREFIRE_PLUGIN["groupId"],
        SUREFIRE_PLUGIN["artifactId"],
        namespace,
    )
    if existing_plugin is None:
        existing_plugin = ET.SubElement(parent, _tag("plugin", namespace))

    _set_child_text_if_missing(existing_plugin, "groupId", SUREFIRE_PLUGIN["groupId"], namespace)
    _set_child_text_if_missing(existing_plugin, "artifactId", SUREFIRE_PLUGIN["artifactId"], namespace)
    _ensure_minimum_plugin_version(existing_plugin, SUREFIRE_PLUGIN["version"], namespace)

    configuration = _get_or_create_child(existing_plugin, "configuration", namespace)
    plugin_dependencies = _get_or_create_child(existing_plugin, "dependencies", namespace)
    if _has_testng_suite_configuration(configuration, namespace):
        _ensure_plugin_dependency(plugin_dependencies, SUREFIRE_PLUGIN["testngProvider"], namespace)
        _remove_plugin_dependency(
            plugin_dependencies,
            SUREFIRE_PLUGIN["junit4Provider"]["groupId"],
            SUREFIRE_PLUGIN["junit4Provider"]["artifactId"],
            namespace,
        )
    else:
        _ensure_plugin_dependency(plugin_dependencies, SUREFIRE_PLUGIN["junit4Provider"], namespace)
        _remove_plugin_dependency(
            plugin_dependencies,
            SUREFIRE_PLUGIN["testngProvider"]["groupId"],
            SUREFIRE_PLUGIN["testngProvider"]["artifactId"],
            namespace,
        )

    includes = _get_or_create_child(configuration, "includes", namespace)
    for include in SUREFIRE_PLUGIN["includes"]:
        _ensure_include(includes, include, namespace)


def _ensure_minimum_plugin_version(plugin: ET.Element, minimum_version: str, namespace: str | None) -> None:
    version = _get_or_create_child(plugin, "version", namespace)
    current_version = _normalise_text(version.text)
    if not current_version:
        version.text = minimum_version
        return

    if _is_maven_property_reference(current_version):
        return

    current_version_tuple = _version_tuple(current_version)
    if current_version_tuple and current_version_tuple < _version_tuple(minimum_version):
        version.text = minimum_version


def _ensure_plugin_dependency(parent: ET.Element, dependency: dict[str, str], namespace: str | None) -> None:
    existing_dependency = _find_artifact(parent, "dependency", dependency["groupId"], dependency["artifactId"], namespace)
    if existing_dependency is None:
        existing_dependency = ET.SubElement(parent, _tag("dependency", namespace))

    for key in ("groupId", "artifactId", "version"):
        _set_child_text_if_missing(existing_dependency, key, dependency[key], namespace)


def _remove_plugin_dependency(parent: ET.Element, group_id: str, artifact_id: str, namespace: str | None) -> None:
    existing_dependency = _find_artifact(parent, "dependency", group_id, artifact_id, namespace)
    if existing_dependency is not None:
        parent.remove(existing_dependency)


def _has_testng_suite_configuration(configuration: ET.Element, namespace: str | None) -> bool:
    suite_xml_files = configuration.find(_tag("suiteXmlFiles", namespace))
    if suite_xml_files is not None and list(suite_xml_files):
        return True

    return _normalise_text(_child_text(configuration, "suiteXmlFiles", namespace)) != ""


def _ensure_include(parent: ET.Element, include: str, namespace: str | None) -> None:
    existing_includes = {_normalise_text(candidate.text) for candidate in _children(parent, "include", namespace)}
    if include in existing_includes:
        return

    include_element = ET.SubElement(parent, _tag("include", namespace))
    include_element.text = include


def _ensure_execution(parent: ET.Element, execution: dict, namespace: str | None) -> None:
    existing_execution = None
    for candidate in _children(parent, "execution", namespace):
        if _child_text(candidate, "id", namespace) == execution["id"]:
            existing_execution = candidate
            break

    if existing_execution is None:
        existing_execution = ET.SubElement(parent, _tag("execution", namespace))

    _set_child_text_if_missing(existing_execution, "id", execution["id"], namespace)
    if "phase" in execution:
        _set_child_text_if_missing(existing_execution, "phase", execution["phase"], namespace)

    goals_element = _get_or_create_child(existing_execution, "goals", namespace)
    existing_goals = {_normalise_text(goal.text) for goal in _children(goals_element, "goal", namespace)}
    for goal in execution["goals"]:
        if goal not in existing_goals:
            goal_element = ET.SubElement(goals_element, _tag("goal", namespace))
            goal_element.text = goal


def _find_artifact(
    parent: ET.Element,
    element_name: str,
    group_id: str,
    artifact_id: str,
    namespace: str | None,
) -> ET.Element | None:
    for candidate in _children(parent, element_name, namespace):
        if (
            _child_text(candidate, "groupId", namespace) == group_id
            and _child_text(candidate, "artifactId", namespace) == artifact_id
        ):
            return candidate
    return None


def _find_plugin(
    parent: ET.Element,
    group_id: str,
    artifact_id: str,
    namespace: str | None,
) -> ET.Element | None:
    for candidate in _children(parent, "plugin", namespace):
        candidate_group_id = _child_text(candidate, "groupId", namespace)
        if candidate_group_id not in ("", group_id):
            continue
        if _child_text(candidate, "artifactId", namespace) == artifact_id:
            return candidate
    return None


def _get_or_create_child(parent: ET.Element, child_name: str, namespace: str | None) -> ET.Element:
    child = parent.find(_tag(child_name, namespace))
    if child is None:
        child = ET.SubElement(parent, _tag(child_name, namespace))
    return child


def _set_child_text_if_missing(parent: ET.Element, child_name: str, value: str, namespace: str | None) -> None:
    child = _get_or_create_child(parent, child_name, namespace)
    if not _normalise_text(child.text):
        child.text = value


def _children(parent: ET.Element, child_name: str, namespace: str | None) -> list[ET.Element]:
    return list(parent.findall(_tag(child_name, namespace)))


def _child_text(parent: ET.Element, child_name: str, namespace: str | None) -> str:
    child = parent.find(_tag(child_name, namespace))
    return "" if child is None else _normalise_text(child.text)


def _normalise_text(text: str | None) -> str:
    return "" if text is None else text.strip()


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def _is_maven_property_reference(version: str) -> bool:
    return bool(re.fullmatch(r"\$\{[^}]+}", version.strip()))


def _namespace(root: ET.Element) -> str | None:
    match = re.match(r"^\{(.+)}", root.tag)
    return None if match is None else match.group(1)


def _tag(name: str, namespace: str | None) -> str:
    return name if namespace is None else f"{{{namespace}}}{name}"
