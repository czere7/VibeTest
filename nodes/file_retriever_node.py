from typing import TYPE_CHECKING

from Extractor import Extractor
from utils import get_working_directory, initial_metric_state, is_concrete_class

if TYPE_CHECKING:
    from AgentState import AgentState


def file_retriever_node(agent_state: "AgentState") -> dict:
    project_dir = get_working_directory()
    print(f"[file_retriever_node] Reading Java source files from: {project_dir}")
    extracted_files = Extractor(str(project_dir)).extract_all()
    test_target_files = [
        source_file
        for source_file in extracted_files
        if is_concrete_class(source_file.file_content)
    ]

    if not test_target_files:
        raise RuntimeError(f"No concrete production Java classes found under WORKING_DIRECTORY: {project_dir}")

    print(
        f"[file_retriever_node] Loaded {len(extracted_files)} Java context files; "
        f"{len(test_target_files)} concrete classes will be tested."
    )

    return {
        "all_files": extracted_files,
        "all_test_files": test_target_files,
        "current_class_index": 0,
        **initial_metric_state(),
    }
