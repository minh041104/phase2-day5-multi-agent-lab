"""Benchmark helpers for single-agent vs multi-agent."""

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return benchmark metrics for one runner/query pair."""

    started = perf_counter()
    state: ResearchState | None = None
    error: Exception | None = None
    try:
        state = runner(query)
    except Exception as exc:  # pragma: no cover - used by CLI benchmark safety path
        error = exc
    latency = perf_counter() - started

    if state is None:
        failed_state = ResearchState.model_validate(
            {
                "request": {"query": query},
                "errors": [str(error) if error else "Unknown benchmark failure"],
            }
        )
        return failed_state, BenchmarkMetrics(
            run_name=run_name,
            latency_seconds=latency,
            failure_rate=1.0,
            quality_score=0.0,
            citation_coverage=0.0,
            notes=str(error) if error else "Unknown benchmark failure",
        )

    citation_coverage = estimate_citation_coverage(state.final_answer)
    failure_rate = 1.0 if state.errors or not state.final_answer else 0.0
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=sum_estimated_cost(state),
        quality_score=estimate_quality_score(state, citation_coverage),
        citation_coverage=citation_coverage,
        failure_rate=failure_rate,
        trace_events=len(state.trace),
        notes="; ".join(state.errors) if state.errors else "ok",
    )
    return state, metrics


def sum_estimated_cost(state: ResearchState) -> float | None:
    total = 0.0
    found = False
    for result in state.agent_results:
        cost = result.metadata.get("cost_usd")
        if isinstance(cost, int | float):
            total += float(cost)
            found = True
    return total if found else None


def estimate_citation_coverage(final_answer: str | None) -> float:
    if not final_answer:
        return 0.0
    claims = [
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", final_answer)
        if len(sentence.strip()) > 30
    ]
    if not claims:
        return 0.0
    cited = [sentence for sentence in claims if re.search(r"\[\d+\]", sentence)]
    return len(cited) / len(claims)


def estimate_quality_score(state: ResearchState, citation_coverage: float) -> float:
    if state.errors or not state.final_answer:
        return 0.0

    score = 4.0
    if state.sources:
        score += 1.0
    if state.research_notes:
        score += 1.5
    if state.analysis_notes:
        score += 1.5
    score += min(citation_coverage, 1.0) * 2.0
    return min(score, 10.0)
