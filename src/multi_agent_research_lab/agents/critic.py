"""Optional critic agent for bonus work."""

import re

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class CriticAgent(BaseAgent):
    """Optional fact-checking and citation-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append lightweight findings."""

        with trace_span(self.name, {"has_final": bool(state.final_answer)}) as span:
            if not state.final_answer:
                state.errors.append("Critic could not evaluate because final_answer is missing.")
                coverage = 0.0
                content = "Missing final answer."
            else:
                coverage = _citation_coverage(state.final_answer)
                content = f"Citation coverage estimate: {coverage:.0%}."
                if coverage < 0.5:
                    state.errors.append(
                        "Citation coverage is below 50%; review unsupported claims."
                    )

            state.agent_results.append(
                AgentResult(
                    agent=AgentName.CRITIC,
                    content=content,
                    metadata={"citation_coverage": coverage},
                )
            )
            span["attributes"]["citation_coverage"] = coverage
            state.add_trace_event(self.name, span)
        return state


def _citation_coverage(answer: str) -> float:
    claims = [
        sentence for sentence in re.split(r"(?<=[.!?])\s+", answer) if len(sentence.strip()) > 30
    ]
    if not claims:
        return 0.0
    cited = [sentence for sentence in claims if re.search(r"\[\d+\]", sentence)]
    return len(cited) / len(claims)
