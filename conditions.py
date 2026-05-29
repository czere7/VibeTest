from typing import Any, Mapping

from utils import get_int_config


def route_after_compile(agent_state: Mapping[str, Any]) -> str:
    if agent_state.get("unrecoverable_error_for_current_class", False):
        return "mutation_validator_node"

    if not agent_state.get("compiler_success", False):
        if agent_state.get("repair_attempts", 0) >= get_int_config("MAX_REPAIR_ATTEMPTS"):
            return "faulty_test_cleanup_node"
        return "test_repair_node"

    active_validation_phase = agent_state.get("active_validation_phase")
    if active_validation_phase == "coverage":
        return "coverage_validator_node"
    if active_validation_phase == "mutation":
        return "mutation_validator_node"

    raise RuntimeError(f"Unknown active_validation_phase: {active_validation_phase}")


def route_after_coverage(agent_state: Mapping[str, Any]) -> str:
    if agent_state.get("unrecoverable_error_for_current_class", False):
        return "mutation_validator_node"
    
    if agent_state.get("coverage_current", 0.0) >= 100.0:
        return "mutation_validator_node"

    if agent_state.get("coverage_iterations", 0) >= get_int_config("MAX_COVERAGE_ITERATIONS"):
        return "mutation_validator_node"

    if agent_state.get("coverage_iterations", 0) == 0:
        return "coverage_test_writer_node"

    if agent_state.get("coverage_improved_significantly", False):
        return "coverage_test_writer_node"

    return "mutation_validator_node"


def route_after_mutation(agent_state: Mapping[str, Any]) -> str:
    if agent_state.get("unrecoverable_error_for_current_class", False):
        return "class_advancer_node"
    
    if agent_state.get("mutation_current", 0.0) >= 100.0:
        return "class_advancer_node"

    if agent_state.get("mutation_iterations", 0) >= get_int_config("MAX_MUTATION_ITERATIONS"):
        return "class_advancer_node"

    if agent_state.get("mutation_iterations", 0) == 0:
        return "mutation_test_writer_node"

    if agent_state.get("mutation_improved_significantly", False):
        return "mutation_test_writer_node"

    return "class_advancer_node"


def route_after_class_advance(agent_state: Mapping[str, Any]) -> str:
    if agent_state["current_class_index"] >= len(agent_state["all_test_files"]):
        return "end"

    return "initial_test_write_node"
