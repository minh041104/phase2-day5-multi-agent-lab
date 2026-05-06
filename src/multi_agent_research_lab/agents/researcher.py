"""Researcher agent implementation."""

from collections.abc import Sequence

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Search for relevant sources, then ask the LLM to summarize source-grounded
        notes that downstream agents can inspect.
        """

        with trace_span(self.name, {"query": state.request.query}) as span:
            sources = self.search_client.search(
                query=state.request.query,
                max_results=state.request.max_sources,
            )
            state.sources = sources
            source_block = _format_sources(sources)
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Researcher in a multi-agent research system. "
                    "Use only the supplied sources. Produce concise research notes with "
                    "numbered source references like [1], [2]."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Sources:\n{source_block}\n\n"
                    "Write source-grounded research notes with the most relevant facts, "
                    "uncertainties, and citations."
                ),
            )
            state.research_notes = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=response.content,
                    metadata={
                        "sources": len(sources),
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )
            span["attributes"]["sources"] = len(sources)
            state.add_trace_event(self.name, span)
        return state


def _format_sources(sources: Sequence[SourceDocument]) -> str:
    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        lines.append(
            f"[{index}] {source.title}\nURL: {source.url or 'no-url'}\nSnippet: {source.snippet}"
        )
    return "\n\n".join(lines) if lines else "No sources returned."
