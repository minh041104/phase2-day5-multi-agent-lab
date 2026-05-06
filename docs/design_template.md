# Design Template

## Problem

Build a research assistant that accepts a long-form user question, gathers web sources, analyzes the evidence, and writes a final source-grounded answer for technical learners.

## Why multi-agent?

The single-agent baseline is useful for comparison, but it mixes retrieval, reasoning, and writing in one opaque step. A multi-agent workflow separates these responsibilities so each handoff can be traced, debugged, benchmarked, and improved independently.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Decide the next route and stop condition | Shared state | Next route in `route_history` | Reaches max iterations before enough context exists |
| Researcher | Gather sources and write source-grounded notes | Query, audience, max sources | `sources`, `research_notes` | Search fails, source snippets are weak or irrelevant |
| Analyst | Extract claims, evidence strength, tradeoffs, and gaps | Research notes and sources | `analysis_notes` | Analysis overstates weak evidence |
| Writer | Produce final answer with bracketed citations | Query, research notes, analysis notes | `final_answer` | Missing citations or unsupported claims |

## Shared state

`ResearchState` is the single handoff object. Key fields: `request` for the user query and audience, `iteration` and `route_history` for routing guardrails, `sources` for citation material, `research_notes` and `analysis_notes` for worker handoff, `final_answer` for the result, `agent_results` for token/cost metadata, `trace` for debug events, and `errors` for failure reporting.

## Routing policy

Graph: `START -> supervisor -> researcher -> supervisor -> analyst -> supervisor -> writer -> supervisor -> END`.

Supervisor policy:

- If `research_notes` is missing, route to `researcher`.
- Else if `analysis_notes` is missing, route to `analyst`.
- Else if `final_answer` is missing, route to `writer`.
- Else route to `done`.
- If `max_iterations` is reached, route to `writer` only when research and analysis are available; otherwise record an error and stop.

## Guardrails

- Max iterations:
- Timeout:
- Retry:
- Fallback:
- Validation:

Defaults:

- Max iterations: `MAX_ITERATIONS`, default 6.
- Timeout: `TIMEOUT_SECONDS`, default 60 seconds for provider calls.
- Retry: OpenAI and Tavily calls retry up to 3 attempts with exponential backoff.
- Fallback: Supervisor stops with an explicit error if it cannot produce enough context before max iterations.
- Validation: Pydantic validates public state, query, source, agent result, and benchmark schemas.

## Benchmark plan

Use the three queries in `configs/lab_default.yaml`. Compare baseline and multi-agent runs on latency, estimated token cost, heuristic quality score, citation coverage, failure rate, and trace event count. Expected outcome: multi-agent should produce more inspectable traces and stronger citation discipline, while baseline should usually be faster and cheaper.
