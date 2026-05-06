"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesize a clear, audience-appropriate answer with citations.
        """

        with trace_span(self.name, {"sources": len(state.sources)}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Writer in a multi-agent research system. "
                    "Write a clear final answer for the requested audience. Cite sources "
                    "with bracketed references like [1], [2] whenever making factual claims."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Research notes:\n{state.research_notes or 'No research notes.'}\n\n"
                    f"Analysis notes:\n{state.analysis_notes or 'No analysis notes.'}\n\n"
                    "Write the final answer. End with a short 'Sources' section listing "
                    "the cited source numbers and titles when available."
                ),
            )
            state.final_answer = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
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
