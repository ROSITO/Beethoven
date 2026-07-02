# PRD - Project Beethoven

## AI Orchestration Platform

> An orchestra is not powerful because every musician plays louder. It is
> powerful because every musician plays the right part, at the right time.

## 1. Vision

Beethoven is a universal orchestration platform for artificial intelligence.

Its mission is not to become the best language model. Its mission is to become
the best conductor: the operating layer that coordinates specialized models,
agents, tools, memories, validators, and future AI runtimes to produce outcomes
that a single model cannot reliably achieve alone.

The project follows three founding principles:

- **Local First**: private or cheap local execution should be preferred when it
  is good enough.
- **Human First**: users remain the artistic and strategic authority.
- **Budget Aware**: every orchestration decision should understand cost,
  latency, and quality tradeoffs.

## 2. Positioning

Beethoven should become more than an agent framework. It should become a
platform where new AI capabilities can be plugged into a stable orchestration
kernel.

The platform must support:

- language models;
- coding agents;
- local tools;
- browser agents;
- validators;
- memory backends;
- approval workflows;
- distributed workers;
- plugin-defined soloists.

## 3. Metaphor

| Musical world | Beethoven |
| --- | --- |
| Conductor | Central orchestrator |
| Score | Execution plan |
| Symphony | Complete workflow |
| Section | Specialized agent group |
| Soloist | Expert AI, agent, provider, or tool |
| Rehearsal | Validation and tests |
| Performance | Execution |
| Encore | Iteration |

## 4. Goals

- Reduce token and provider costs.
- Use multiple AI systems as one coordinated team.
- Centralize provider access behind stable contracts.
- Preserve project memory outside stateless agents.
- Make every routing and execution decision traceable.
- Keep humans in the loop for risky or expensive actions.
- Allow new models, agents, and tools to attach without rewriting the conductor.

## 5. Non-Goals

- Beethoven is not a thin wrapper around one provider.
- Beethoven is not a prompt collection.
- Beethoven is not a chatbot UI first.
- Beethoven should not hide orchestration decisions from the user.

## 6. Core Architecture

```text
User / API / CLI / Dashboard
          |
      Intent Layer
          |
      Score Layer
          |
   Conductor Engine
          |
  +-------+--------+----------+
  |       |        |          |
Router  Memory   Budget   Governance
  |
  +------------+-------------+-------------+
  |            |             |             |
Local LLM    Claude        Codex        Tools
  |            |             |             |
  +------------+-------------+-------------+
          |
       Critic
          |
      Validator
          |
   Final Symphony
```

## 7. Modules

### Conductor

Coordinates score execution and delegates task work to soloists.

### Score

Represents an inspectable, replayable execution plan.

### Router

Chooses the best soloist for each task based on capability, cost, quality,
latency, privacy, locality, and policy.

### Budget Manager

Estimates, tracks, and optimizes token, money, latency, and compute budgets.

### Memory

Stores project knowledge, execution traces, user preferences, semantic cache,
and reusable decisions.

### Critic

Reviews outputs for correctness, coherence, policy compliance, and fit to the
user's intent.

### Validator

Runs tests, lint, type checks, security scans, git diffs, and domain-specific
verification.

### Governance

Handles approvals, permissions, secrets, audit logs, and observability.

## 8. MVP Scope

The MVP should prove the orchestration loop before building a large UI.

Required:

- Python package with stable core contracts.
- CLI for running a score.
- Desktop workbench inspired by Codex Desktop, Claude Desktop, and ZCode
  Desktop.
- JSON score serialization.
- Local echo soloist for deterministic testing.
- Ollama adapter.
- OpenAI-compatible adapter.
- Codex workflow adapter.
- Basic policy router.
- Execution trace output.
- Validation hooks.
- Human approval gates for risky tasks.

### Current MVP Status

As of 2026-07-02, Beethoven has crossed from concept into a working pre-alpha:

| Area | Status | Notes |
| --- | --- | --- |
| Core score/conductor/runtime contracts | Done | `Task`, `Score`, `Soloist`, router, conductor, trace, serialization. |
| Terminal CLI | Done | `beethoven chat`, `score`, `run`, sessions, workspace, soloists, skills, orchestrator, SoloMLX. |
| Desktop workbench | In progress | Working local API, Beethoven Auto routing by default, fallback when routed adapters fail, score preview, central chat streaming/final response, session restore/clear, file attachments, runtime board. |
| Hidden Beethoven orchestrator | Done | Local conductor uses SoloMLX/OpenAI-compatible `/v1` first, then Ollama. It is not user-selectable. |
| SoloMLX runtime brick | Done | Managed runtime class, install, prepare Ministral, start, stop, status, ensure/autostart policy, memory guardrails, desktop API. |
| Ollama adapter | Done | Available when explicitly enabled and model exists. |
| OpenAI-compatible adapter | Done | Hidden orchestrator and execution-side `openai-compatible` soloist with CLI/API/desktop config. |
| Codex/Claude adapters | Done | Local CLI adapters are available when installed and logged in. |
| RecursiveMAS integration | Partial | Native recursive scores and optional sidecar bridge are present; deeper runtime collaboration remains experimental. |
| `@path` attachments | Done | Safe workspace reads with binary blocking, MIME/size/snippet metadata, total byte budget, bounded directory bundles, natural-language current-folder inference, workspace structure manifest, and desktop inspection. |
| Validation tasks | In progress | Local commands and named profiles are appended as governed `validate` score tasks with policy gating, exact command approval, composer command input, desktop review/approve/rerun panel, and inspector details for stdout/stderr. |
| Diff/patch workflow | In progress | Bounded Git diff and approval-token patch check/apply are available in CLI, desktop API, desktop session menu, and chat-visible review messages, with patch summaries and bounded side-by-side preview. |
| Production packaging | Partial | Tauri dev mode now compiles and launches with Cargo, versioned sidecar launchers, target-suffixed sidecar, icon placeholder, external binary config, and packaging doctor; installer-grade bundled Python runtime remains. |

### MVP Acceptance Criteria

The MVP is acceptable when:

- A user opens the desktop to an empty task state and can run a first objective
  without prefilled demo content.
- Beethoven's hidden local orchestrator drafts the score by default through the
  managed SoloMLX/Ministral runtime when available.
- Beethoven treats SoloMLX as an internal runtime dependency with explicit
  ensure/autostart policy, not as a user-selected conductor.
- The user can see whether the conductor, SoloMLX, RecursiveMAS, Codex, Claude,
  Ollama, and deterministic fallback are available.
- The desktop conversation shows normal user and assistant message flow, while
  the score inspector shows task planning/execution separately.
- Attached `@path` files are visible, bounded, and included in model context.
- Runs stream planned score, task state, selected soloist, validation, and final
  synthesis without waiting for the final context only.
- Risky actions are gated by permission policy before execution.
- The terminal CLI can perform every important desktop action.
- Tauri dev mode can launch a working app backed by a predictable Python
  sidecar strategy.

### Immediate Product Tranches

P0:

- finish the desktop first-run state, runtime board, and conversation/run split;
- test SoloMLX/Ministral on-device as the default hidden conductor path and tune
  runtime diagnostics for real memory/load behavior;
- deepen generated-code review tooling on top of the patch preview.

P1:

- deepen governed code actions beyond patch summary/apply;
- deepen RecursiveMAS collaboration beyond the bridge protocol;
- add semantic memory/cache;
- package Tauri with the Python sidecar and managed local runtime checks; keep
  `beethoven package doctor` as the local readiness gate.

Deferred:

- marketplace;
- distributed execution;
- advanced dashboard;
- multi-tenant cloud;
- fine-grained enterprise RBAC.

## 9. Technical Principles

- Provider adapters live at the edge.
- Scores are portable and serializable.
- Agents stay stateless.
- Memory is explicit and externalized.
- Routing is policy-driven.
- Validation is part of execution.
- Observability is built in from the start.
- Security defaults should be conservative.

## 10. Roadmap

### Phase I: Solo

Stable score model, conductor, registry, router, deterministic tests, CLI, and
desktop product contract.

### Phase II: Ensemble

Provider adapters, validation hooks, memory interface, semantic cache.

### Phase III: Orchestra

Parallel execution, critic loops, approval gates, policy routing, cost dashboard.

### Phase IV: Philharmonic

Plugin SDK, marketplace, hybrid local/cloud execution, distributed workers,
advanced governance, public API.

## 11. Success Metrics

- A new provider can be added without changing the conductor.
- A score can be inspected, replayed, and traced.
- Local execution is used when it satisfies quality and privacy constraints.
- Costs are visible before and after execution.
- Validation failures are surfaced before final synthesis.
- Users can approve, reject, or redirect high-impact actions.

## 12. Long-Term Vision

Beethoven becomes the operating system of artificial intelligence: every AI is a
specialized musician, every task is a score, every project is a symphony, and
the user remains the creative authority.

The success of Beethoven will not be measured by the power of one model. It will
be measured by the quality of orchestration between many excellent ones.
