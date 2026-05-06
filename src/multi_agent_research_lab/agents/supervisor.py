"""Supervisor / router implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        Inspect state, choose one of researcher/analyst/writer/done, and enforce
        the configured max-iteration guardrail.
        """

        with trace_span(
            self.name,
            {
                "iteration": state.iteration,
                "has_research": bool(state.research_notes),
                "has_analysis": bool(state.analysis_notes),
                "has_final": bool(state.final_answer),
            },
        ) as span:
            route = self._choose_route(state)
            state.record_route(route)
            span["attributes"]["route"] = route
            state.add_trace_event(self.name, span)
        return state

    def _choose_route(self, state: ResearchState) -> str:
        if state.final_answer:
            return "done"

        if state.iteration >= self.settings.max_iterations:
            if state.research_notes and state.analysis_notes:
                return "writer"
            state.errors.append(
                f"Stopped after reaching max_iterations={self.settings.max_iterations} "
                "before enough context was available to write a final answer."
            )
            return "done"

        if not state.research_notes:
            return "researcher"
        if not state.analysis_notes:
            return "analyst"
        if not state.final_answer:
            return "writer"
        return "done"
