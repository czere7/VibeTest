from io import BytesIO

from PIL import Image
from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.graph import END, START, StateGraph

from AgentState import AgentState
from conditions import (
    route_after_class_advance,
    route_after_compile,
    route_after_coverage,
    route_after_mutation,
)
from nodes.class_advancer_node import class_advancer_node
from nodes.compiler_node import compiler_node
from nodes.coverage_test_writer_node import coverage_test_writer_node
from nodes.coverage_validator_node import coverage_validator_node
from nodes.dependency_resolver_node import dependency_resolver_node
from nodes.faulty_test_cleanup_node import faulty_test_cleanup_node
from nodes.file_retriever_node import file_retriever_node
from nodes.initial_test_write_node import initial_test_write_node
from nodes.mutation_test_writer_node import mutation_test_writer_node
from nodes.mutation_validator_node import mutation_validator_node
from nodes.test_repair_node import test_repair_node


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("file_retriever_node", file_retriever_node)
    graph.add_node("dependency_resolver_node", dependency_resolver_node)
    graph.add_node("initial_test_write_node", initial_test_write_node)
    graph.add_node("compiler_node", compiler_node)
    graph.add_node("test_repair_node", test_repair_node)
    graph.add_node("coverage_validator_node", coverage_validator_node)
    graph.add_node("coverage_test_writer_node", coverage_test_writer_node)
    graph.add_node("mutation_validator_node", mutation_validator_node)
    graph.add_node("mutation_test_writer_node", mutation_test_writer_node)
    graph.add_node("class_advancer_node", class_advancer_node)
    graph.add_node("faulty_test_cleanup_node", faulty_test_cleanup_node)

    graph.add_edge(START, "file_retriever_node")
    graph.add_edge("file_retriever_node", "dependency_resolver_node")
    graph.add_edge("dependency_resolver_node", "initial_test_write_node")
    graph.add_edge("initial_test_write_node", "compiler_node")
    graph.add_edge("test_repair_node", "compiler_node")
    graph.add_edge("coverage_test_writer_node", "compiler_node")
    graph.add_edge("mutation_test_writer_node", "compiler_node")
    graph.add_edge("faulty_test_cleanup_node", "class_advancer_node")

    graph.add_conditional_edges(
        "compiler_node",
        route_after_compile,
        {
            "test_repair_node": "test_repair_node",
            "coverage_validator_node": "coverage_validator_node",
            "mutation_validator_node": "mutation_validator_node",
            "faulty_test_cleanup_node": "faulty_test_cleanup_node",
        },
    )
    graph.add_conditional_edges(
        "coverage_validator_node",
        route_after_coverage,
        {
            "coverage_test_writer_node": "coverage_test_writer_node",
            "mutation_validator_node": "mutation_validator_node",
        },
    )
    graph.add_conditional_edges(
        "mutation_validator_node",
        route_after_mutation,
        {
            "mutation_test_writer_node": "mutation_test_writer_node",
            "class_advancer_node": "class_advancer_node",
        },
    )
    graph.add_conditional_edges(
        "class_advancer_node",
        route_after_class_advance,
        {
            "initial_test_write_node": "initial_test_write_node",
            "end": END,
        },
    )

    return graph.compile()


app = build_graph()


def main():
    # image = Image.open(BytesIO(app.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)))
    # image.show()
    app.invoke({})


if __name__ == "__main__":
    main()
