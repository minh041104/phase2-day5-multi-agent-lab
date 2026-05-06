from multi_agent_research_lab.services.search_client import SearchClient


class FakeTavilyClient:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def search(self, **kwargs: object) -> dict[str, object]:
        self.kwargs = kwargs
        return {
            "results": [
                {
                    "title": "Result title",
                    "url": "https://example.com/result",
                    "content": "Result snippet",
                    "score": 0.9,
                }
            ]
        }


def test_search_client_maps_tavily_results() -> None:
    fake_client = FakeTavilyClient()
    client = SearchClient(client=fake_client)

    results = client.search("agent systems", max_results=3)

    assert len(results) == 1
    assert results[0].title == "Result title"
    assert results[0].url == "https://example.com/result"
    assert results[0].snippet == "Result snippet"
    assert results[0].metadata["provider"] == "tavily"
    assert fake_client.kwargs["query"] == "agent systems"
    assert fake_client.kwargs["max_results"] == 3
    assert fake_client.kwargs["search_depth"] == "basic"
