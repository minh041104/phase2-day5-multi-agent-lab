"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import ConfigurationError, ExternalServiceError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client."""

    def __init__(self, client: Any | None = None, settings: Settings | None = None) -> None:
        self._client = client
        self._settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        Connect to OpenAI through the Responses API. Retry, timeout, and token/cost
        accounting live here rather than inside individual agents.
        """

        if not self._settings.openai_api_key and self._client is None:
            raise ConfigurationError("OPENAI_API_KEY is required to call the LLM provider")

        try:
            response = self._complete_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        # Provider-specific exceptions vary by SDK version.
        except Exception as exc:  # pragma: no cover
            raise ExternalServiceError(f"OpenAI completion failed: {exc}") from exc

        content = _extract_output_text(response)
        if not content:
            raise ExternalServiceError("OpenAI completion returned an empty response")

        usage = getattr(response, "usage", None)
        input_tokens = _usage_value(usage, "input_tokens", "prompt_tokens")
        output_tokens = _usage_value(usage, "output_tokens", "completion_tokens")
        cost_usd = _estimate_cost(self._settings.openai_model, input_tokens, output_tokens)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _complete_with_retry(self, system_prompt: str, user_prompt: str) -> Any:
        client = self._client or _build_openai_client(
            timeout_seconds=self._settings.timeout_seconds
        )
        self._client = client
        return client.responses.create(
            model=self._settings.openai_model,
            instructions=system_prompt,
            input=user_prompt,
            timeout=self._settings.timeout_seconds,
        )


def _build_openai_client(timeout_seconds: int) -> Any:
    try:
        from openai import OpenAI
    # Exercised only without optional dependency.
    except ImportError as exc:  # pragma: no cover
        raise ConfigurationError(
            'Install OpenAI support with: python -m pip install -e ".[llm]"'
        ) from exc

    return OpenAI(timeout=timeout_seconds)


def _extract_output_text(response: Any) -> str:
    output_text = _value(response, "output_text")
    if isinstance(output_text, str):
        return output_text.strip()
    return ""


def _usage_value(usage: Any, *names: str) -> int | None:
    if usage is None:
        return None
    for name in names:
        value = _value(usage, name)
        if isinstance(value, int):
            return value
    return None


def _value(container: Any, name: str) -> Any:
    if isinstance(container, dict):
        return container.get(name)
    return getattr(container, name, None)


def _estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None

    price_per_million = {
        "gpt-5.4-mini": (0.75, 4.50),
        "gpt-5.4": (2.50, 15.00),
        "gpt-5.5": (5.00, 30.00),
        "gpt-4o-mini": (0.15, 0.60),
    }
    normalized = model.lower()
    if normalized not in price_per_million:
        return None

    input_price, output_price = price_per_million[normalized]
    return (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)
