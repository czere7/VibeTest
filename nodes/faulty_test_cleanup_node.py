from pathlib import Path
from typing import TYPE_CHECKING

from utils import ensure_file

if TYPE_CHECKING:
    from AgentState import AgentState


def faulty_test_cleanup_node(agent_state: "AgentState") -> dict:
    print(f"Faulty Test Cleanup Node. unrecoverable_error_for_current_class:{agent_state.get('unrecoverable_error_for_current_class', 'default')}")
    if agent_state.get('unrecoverable_error_for_current_class', False):
        return {}
    
    last_compilable_test_class = agent_state.get("last_compilable_test_class", "").strip()
    last_compilable_test_file_path = agent_state.get("last_compilable_test_file_path", "")
    if last_compilable_test_class and last_compilable_test_file_path:
        print(
            "[faulty_test_cleanup_node] Repair attempts exhausted. "
            f"Restoring last compilable test file: {last_compilable_test_file_path}"
        )
        last_compilable_path = ensure_file(last_compilable_test_file_path)
        last_compilable_path.write_text(last_compilable_test_class + "\n", encoding="utf-8")
        return {
            "test_class": "",
            "compiler_success": False,
            "compiler_feedback": "",
            "test_file_path": "",
            "repair_attempts": 0,
        }

    test_file_path = agent_state.get("test_file_path", "")
    if test_file_path:
        test_path = Path(test_file_path)
        if test_path.is_file():
            test_path.unlink()
            print(
                "[faulty_test_cleanup_node] Repair attempts exhausted and no compilable snapshot exists. "
                f"Deleted faulty test file: {test_file_path}"
            )
        else:
            print(
                "[faulty_test_cleanup_node] Repair attempts exhausted and no compilable snapshot exists. "
                f"No test file found to delete at: {test_file_path}"
            )
    else:
        print("[faulty_test_cleanup_node] Repair attempts exhausted and no test file path was available.")

    return {
        "test_class": "",
        "compiler_success": False,
        "compiler_feedback": "",
        "test_file_path": "",
        "repair_attempts": 0,
    }
