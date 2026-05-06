"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Extract key claims, compare evidence, and flag weak or missing support.
        """

        with trace_span(self.name, {"sources": len(state.sources)}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Analyst in a multi-agent research system. "
                    "Transform research notes into structured insights. Keep citation "
                    "markers from the notes when discussing evidence."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Research notes:\n{state.research_notes or 'No research notes.'}\n\n"
                    "Produce analysis with these sections: Key claims, Evidence strength, "
                    "Tradeoffs or disagreements, Gaps and risks."
                ),
            )
            state.analysis_notes = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )
            state.add_trace_event(self.name, span)
        return state
