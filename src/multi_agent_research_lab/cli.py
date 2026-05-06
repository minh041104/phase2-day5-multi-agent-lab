"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from typing import Annotated

import typer
import yaml  # type: ignore[import-untyped]
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import LabError
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    BenchmarkMetrics,
    ResearchQuery,
    SourceDocument,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    load_dotenv()
    settings = get_settings()
    configure_logging(settings.log_level)


def run_single_agent(query: str) -> ResearchState:
    """Run the single-agent baseline with real search and LLM calls."""

    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    search_client = SearchClient()
    llm_client = LLMClient()

    with trace_span("baseline", {"query": request.query}) as span:
        sources = search_client.search(query=request.query, max_results=request.max_sources)
        state.sources = sources
        response = llm_client.complete(
            system_prompt=(
                "You are a single-agent research assistant. Search results have already "
                "been gathered for you. Research, analyze, and write the final answer in "
                "one pass. Cite sources with bracketed references like [1], [2]."
            ),
            user_prompt=(
                f"Question: {request.query}\n"
                f"Audience: {request.audience}\n\n"
                f"Sources:\n{_format_sources(sources)}\n\n"
                "Write a concise, source-grounded answer and include a short Sources section."
            ),
        )
        state.final_answer = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.BASELINE,
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
        state.add_trace_event("baseline", span)
    return state


def run_multi_agent_query(query: str) -> ResearchState:
    """Run the multi-agent workflow for benchmark reuse."""

    return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline."""

    _init()
    try:
        state = run_single_agent(query)
    except LabError as exc:
        console.print(Panel.fit(str(exc), title="Run failed", style="red"))
        raise typer.Exit(code=1) from exc
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except LabError as exc:
        console.print(Panel.fit(str(exc), title="Run failed", style="red"))
        raise typer.Exit(code=1) from exc
    console.print(result.model_dump_json(indent=2))


@app.command("benchmark")
def benchmark(
    config_path: Annotated[
        Path,
        typer.Option("--config", help="YAML config containing benchmark.queries"),
    ] = Path("configs/lab_default.yaml"),
    output_path: Annotated[
        Path,
        typer.Option("--output", help="Markdown report output path"),
    ] = Path("reports/benchmark_report.md"),
) -> None:
    """Run baseline and multi-agent benchmarks and write a markdown report."""

    _init()
    queries = _load_benchmark_queries(config_path)
    metrics: list[BenchmarkMetrics] = []

    for index, query in enumerate(queries, start=1):
        _, baseline_metrics = run_benchmark(
            run_name=f"baseline-q{index}",
            query=query,
            runner=run_single_agent,
        )
        metrics.append(baseline_metrics)

        _, multi_metrics = run_benchmark(
            run_name=f"multi-agent-q{index}",
            query=query,
            runner=run_multi_agent_query,
        )
        metrics.append(multi_metrics)

    report = render_markdown_report(metrics)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    console.print(Panel.fit(f"Wrote {output_path}", title="Benchmark"))


def _load_benchmark_queries(config_path: Path) -> list[str]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    benchmark_config = config.get("benchmark", {})
    queries = benchmark_config.get("queries", [])
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise typer.BadParameter("Config must contain benchmark.queries as a list of strings")
    return queries


def _format_sources(sources: list[SourceDocument]) -> str:
    if not sources:
        return "No sources returned."
    return "\n\n".join(
        f"[{index}] {source.title}\nURL: {source.url or 'no-url'}\nSnippet: {source.snippet}"
        for index, source in enumerate(sources, start=1)
    )


if __name__ == "__main__":
    app()
