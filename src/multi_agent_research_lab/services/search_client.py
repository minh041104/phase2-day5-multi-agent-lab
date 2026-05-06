"""Search client abstraction for ResearcherAgent."""

from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import ConfigurationError, ExternalServiceError
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client."""

    def __init__(self, client: Any | None = None, settings: Settings | None = None) -> None:
        self._client = client
        self._settings = settings or get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Use Tavily as the default web search provider and normalize results into the
        public `SourceDocument` schema used by agents and benchmark reports.
        """

        if not self._settings.tavily_api_key and self._client is None:
            raise ConfigurationError("TAVILY_API_KEY is required to call the search provider")

        try:
            response = self._search_with_retry(query=query, max_results=max_results)
        # Provider-specific exceptions vary by SDK version.
        except Exception as exc:  # pragma: no cover
            raise ExternalServiceError(f"Tavily search failed: {exc}") from exc

        results = _value(response, "results")
        if not isinstance(results, list):
            return []

        documents: list[SourceDocument] = []
        for index, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or f"Source {index}")
            snippet = str(
                item.get("content") or item.get("snippet") or item.get("raw_content") or ""
            )
            documents.append(
                SourceDocument(
                    title=title,
                    url=_optional_str(item.get("url")),
                    snippet=snippet,
                    metadata={
                        "score": item.get("score"),
                        "provider": "tavily",
                        "rank": index,
                    },
                )
            )
        return documents

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _search_with_retry(self, query: str, max_results: int) -> Any:
        client = self._client or _build_tavily_client(self._settings.tavily_api_key)
        self._client = client
        return client.search(query=query, max_results=max_results, search_depth="basic")


def _build_tavily_client(api_key: str | None) -> Any:
    if not api_key:
        raise ConfigurationError("TAVILY_API_KEY is required to call the search provider")

    try:
        from tavily import TavilyClient  # type: ignore[import-not-found]
    # Exercised only without optional dependency.
    except ImportError as exc:  # pragma: no cover
        raise ConfigurationError(
            "Install Tavily support with: python -m pip install tavily-python"
        ) from exc

    return TavilyClient(api_key=api_key)


def _value(container: Any, name: str) -> Any:
    if isinstance(container, dict):
        return container.get(name)
    return getattr(container, name, None)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
