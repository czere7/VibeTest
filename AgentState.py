from typing import TypedDict, Sequence, Annotated, List

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from utils import SourceCodeFileData


class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    current_class_index: int
    all_files: List[SourceCodeFileData]
    all_test_files: List[SourceCodeFileData]
    test_class: str
    compiler_success: bool
    compiler_feedback: str
    test_file_path: str
    last_compilable_test_class: str
    last_compilable_test_file_path: str
    coverage_previous: float
    coverage_current: float
    coverage_delta: float
    coverage_improved_significantly: bool
    coverage_feedback: str
    mutation_previous: float
    mutation_current: float
    mutation_delta: float
    mutation_improved_significantly: bool
    mutation_feedback: str
    active_validation_phase: str
    repair_attempts: int
    coverage_iterations: int
    mutation_iterations: int
    unrecoverable_error_for_current_class: bool
