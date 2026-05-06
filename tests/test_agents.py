from types import SimpleNamespace

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMClient, LLMResponse


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if "Researcher" in system_prompt:
            content = "Research notes cite the source [1]."
        elif "Analyst" in system_prompt:
            content = "Key claims are supported by source [1]."
        elif "Writer" in system_prompt:
            content = "Final answer with a cited claim [1]."
        else:
            content = f"Fallback response for {user_prompt}"
        return LLMResponse(content=content, input_tokens=10, output_tokens=5, cost_usd=0.001)


class FakeSearch:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        return [
            SourceDocument(
                title="Agent Systems Guide",
                url="https://example.com/agents",
                snippet=f"Relevant source for {query}; max={max_results}",
            )
        ]


def test_supervisor_routes_through_required_steps() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    supervisor = SupervisorAgent()

    supervisor.run(state)
    assert state.route_history[-1] == "researcher"

    state.research_notes = "Research notes [1]"
    supervisor.run(state)
    assert state.route_history[-1] == "analyst"

    state.analysis_notes = "Analysis notes [1]"
    supervisor.run(state)
    assert state.route_history[-1] == "writer"

    state.final_answer = "Final answer [1]"
    supervisor.run(state)
    assert state.route_history[-1] == "done"


def test_workflow_completes_with_fake_clients() -> None:
    llm = FakeLLM()
    workflow = MultiAgentWorkflow(
        researcher=ResearcherAgent(search_client=FakeSearch(), llm_client=llm),
        analyst=AnalystAgent(llm_client=llm),
        writer=WriterAgent(llm_client=llm),
    )
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))

    result = workflow.run(state)

    assert result.final_answer == "Final answer with a cited claim [1]."
    assert result.route_history == ["researcher", "analyst", "writer", "done"]
    assert len(result.sources) == 1
    assert len(result.agent_results) == 3


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            output_text="hello from fake openai",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_llm_client_maps_mock_openai_response() -> None:
    fake_client = FakeOpenAIClient()
    settings = Settings(OPENAI_MODEL="gpt-5.4-mini")
    client = LLMClient(client=fake_client, settings=settings)

    response = client.complete("system", "user")

    assert response.content == "hello from fake openai"
    assert response.input_tokens == 100
    assert response.output_tokens == 20
    assert response.cost_usd is not None
    assert fake_client.responses.kwargs["model"] == "gpt-5.4-mini"
