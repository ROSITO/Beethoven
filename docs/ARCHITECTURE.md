# Beethoven Architecture

Beethoven is designed as a universal orchestration platform for AI systems.
The goal is not to wrap one provider better than everyone else, but to make any
model, agent, tool, workflow, or future AI runtime composable through stable
contracts.

## Platform Layers

1. **Intent Layer**: understands the user's objective, constraints, risk level,
   privacy needs, and budget.
2. **Orchestrator Layer**: Beethoven's private local planning model converts
   intent into a routing-aware score proposal. It can use the managed SoloMLX
   runtime through an OpenAI-compatible `/v1` API or Ollama, and it is not a
   user-selected soloist.
3. **Score Layer**: converts intent into a portable execution plan made of
   ordered tasks, dependencies, capabilities, and validation gates.
4. **Routing Layer**: selects the right soloist for each task according to
   capability, cost, latency, quality, locality, and policy.
5. **Execution Layer**: runs tasks through provider adapters, agent runtimes,
   local tools, or distributed workers.
6. **Critic Layer**: reviews intermediate and final outputs across correctness,
   coherence, safety, and user fit.
7. **Validation Layer**: runs tests, lint, type checks, security checks, git
   diffs, or domain-specific verification.
8. **Memory Layer**: stores project knowledge, execution traces, reusable
   decisions, and semantic cache entries outside of stateless agents.
9. **Governance Layer**: provides human approval gates, audit logs, permissions,
   secrets management, and observability.

## Core Contracts

The first implementation exposes deliberately small primitives:

- `Task`: one unit of work with an instruction, required capability, and
  dependencies.
- `Score`: the complete execution plan.
- `Soloist`: a provider, model, agent, tool, or worker that can perform tasks.
- `SoloistResult`: normalized output, cost, token, and metadata envelope.
- `SoloistRegistry`: registration surface for orchestratable intelligence.
- `CapabilityRouter`: deterministic baseline router.
- `Conductor`: score executor that coordinates tasks without owning provider
  details.
- `LocalOrchestrator`: hidden planning boundary used by Beethoven before
  execution routing. It may suggest task-level soloists, but the router only
  accepts suggestions that are registered and capable.
- `SoloMLXRuntime`: managed local MLX brick backed by `ROSITO/SoloMLX-server`.
  It is installed and started by Beethoven, then consumed through the same
  OpenAI-compatible adapter boundary.

These contracts are the foundation for the future plugin SDK. A plugin should
be able to add a new model, local tool, remote worker, policy, validator, or
memory backend without rewriting the conductor.

## Design Principles

- **Universal over provider-specific**: provider adapters are edges, not the
  center of the architecture.
- **Scores are portable**: a plan should be inspectable, serializable, and
  replayable.
- **Agents stay stateless**: durable memory belongs in explicit storage layers.
- **Routing is policy-driven**: quality, privacy, cost, speed, and locality are
  first-class routing signals.
- **Human approval is native**: risky actions should pause for review.
- **Validation is part of execution**: orchestration is incomplete without proof.
- **Observability by default**: every decision should be traceable.

## Near-Term Milestones

1. Add JSON serialization for scores and execution traces.
2. Add provider adapters for local echo, Ollama, OpenAI-compatible APIs, and
   Codex workflows.
3. Add policy-based routing with cost, privacy, latency, and model quality
   signals.
4. Add validator hooks for tests, lint, git diffs, and custom commands.
5. Add a CLI that can run a score file and print the final symphony.
