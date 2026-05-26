from typing import TYPE_CHECKING

from utils import advance_to_next_class

if TYPE_CHECKING:
    from AgentState import AgentState


def class_advancer_node(agent_state: "AgentState") -> dict:
    next_index = agent_state["current_class_index"] + 1
    total = len(agent_state.get("all_test_files", []))
    print(f"[class_advancer_node] Advancing to next class: index {next_index + 1}/{total}.")
    return advance_to_next_class(agent_state)
