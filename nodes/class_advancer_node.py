from pathlib import Path
from typing import TYPE_CHECKING

from utils import advance_to_next_class, persist_current_class_index, config, log_serious_error
import os

if TYPE_CHECKING:
    from AgentState import AgentState


def class_advancer_node(agent_state: "AgentState") -> dict:
    if agent_state.get("unrecoverable_error_for_current_class", False):
        log_serious_error(f'Failed to create tests for class {current_class_index}')

    next_index = agent_state["current_class_index"] + 1
    total = len(agent_state.get("all_test_files", []))
    if next_index == total:
        if os.path.exists(config.get("CLASS_INDEX_TMP_FILE", "tmp.txt")):
            Path(config.get("CLASS_INDEX_TMP_FILE", "tmp.txt")).unlink()
    else:
        persist_current_class_index(next_index)
    print(f"[class_advancer_node] Advancing to next class: index {next_index + 1}/{total}.")
    return advance_to_next_class(agent_state)
