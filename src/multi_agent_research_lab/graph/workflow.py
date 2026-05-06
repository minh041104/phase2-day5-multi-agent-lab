"""LangGraph workflow implementation."""

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.state import ResearchState


class WorkflowState(TypedDict, total=False):
    """Serialized ResearchState shape carried through LangGraph."""

    request: dict[str, Any]
    iteration: int
    route_history: list[str]
    sources: list[dict[str, Any]]
    research_notes: str | None
    analysis_notes: str | None
    final_answer: str | None
    agent_results: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    errors: list[str]


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(
        self,
        supervisor: SupervisorAgent | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()
        self._compiled: Any | None = None

    def build(self) -> Any:
        """Create a LangGraph graph.

        Nodes are intentionally simple wrappers around agent classes. Routing remains
        centralized in `SupervisorAgent`.
        """

        builder = StateGraph(WorkflowState)
        builder.add_node("supervisor", self._run_supervisor)
        builder.add_node("researcher", self._run_researcher)
        builder.add_node("analyst", self._run_analyst)
        builder.add_node("writer", self._run_writer)

        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges(
            "supervisor",
            _next_route,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )
        builder.add_edge("researcher", "supervisor")
        builder.add_edge("analyst", "supervisor")
        builder.add_edge("writer", "supervisor")
        return builder.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.

        Compile lazily, invoke LangGraph with a serialized state, then validate the
        returned value back into the public `ResearchState` schema.
        """

        graph = self._compiled or self.build()
        self._compiled = graph
        result = graph.invoke(_dump_state(state))
        return ResearchState.model_validate(result)

    def _run_supervisor(self, state: WorkflowState) -> WorkflowState:
        return _dump_state(self.supervisor.run(ResearchState.model_validate(state)))

    def _run_researcher(self, state: WorkflowState) -> WorkflowState:
        return _dump_state(self.researcher.run(ResearchState.model_validate(state)))

    def _run_analyst(self, state: WorkflowState) -> WorkflowState:
        return _dump_state(self.analyst.run(ResearchState.model_validate(state)))

    def _run_writer(self, state: WorkflowState) -> WorkflowState:
        return _dump_state(self.writer.run(ResearchState.model_validate(state)))


def _dump_state(state: ResearchState) -> WorkflowState:
    return {
        "request": state.request.model_dump(mode="python"),
        "iteration": state.iteration,
        "route_history": state.route_history,
        "sources": [source.model_dump(mode="python") for source in state.sources],
        "research_notes": state.research_notes,
        "analysis_notes": state.analysis_notes,
        "final_answer": state.final_answer,
        "agent_results": [result.model_dump(mode="python") for result in state.agent_results],
        "trace": state.trace,
        "errors": state.errors,
    }


def _next_route(state: WorkflowState) -> Literal["researcher", "analyst", "writer", "done"]:
    route_history = state.get("route_history") or []
    if not route_history:
        return "done"

    route = route_history[-1]
    if route == "researcher":
        return "researcher"
    if route == "analyst":
        return "analyst"
    if route == "writer":
        return "writer"
    if route == "done":
        return "done"
    return "done"
