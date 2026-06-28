# Beethoven

**The AI Operating System**

**One conductor. Many soloists. One symphony.**

> The future of AI is not a bigger model. It is better orchestration.

![Status](https://img.shields.io/badge/status-pre--alpha-orange)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Why Beethoven?

Beethoven is an open-source platform for universal AI orchestration. Its goal is
to make models, agents, tools, validators, memories, and future AI runtimes work
together through one coherent operating layer.

Instead of asking a single LLM to solve everything, Beethoven:

- understands the user's intent;
- decomposes the work into a portable `Score`;
- chooses the best soloist for each task;
- coordinates execution across models, agents, and tools;
- validates results with tests, critics, policies, and human approval gates;
- delivers one coherent final answer.

The user is the composer. Beethoven is the conductor.

## Current Foundation

This repository now contains the first executable orchestration kernel:

- `Task`: one unit of work.
- `Score`: the execution plan.
- `Soloist`: any model, agent, provider, tool, or worker.
- `SoloistRegistry`: registry of available soloists.
- `CapabilityRouter`: deterministic baseline routing.
- `Conductor`: dependency-aware score execution.
- `beethoven` CLI: terminal surface for creating and running scores.
- `OllamaSoloist`: first real local model adapter when Ollama is available.
- `@path` attachments: safe workspace file context with size limits.
- Run events: score/task/validation events for desktop streaming.

The first implementation is intentionally small. The foundation must stay stable
enough for future providers and plugins to attach naturally.

## Example

```python
from dataclasses import dataclass

from beethoven import (
    Capability,
    CapabilityRouter,
    Conductor,
    ExecutionContext,
    Score,
    SoloistRegistry,
    SoloistResult,
    Task,
)


@dataclass(frozen=True)
class LocalSoloist:
    name: str
    capabilities: frozenset[Capability]

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        return SoloistResult(output=f"{self.name} performed {task.id}")


registry = SoloistRegistry()
registry.register(LocalSoloist("planner", frozenset({Capability.PLAN})))
registry.register(LocalSoloist("coder", frozenset({Capability.CODE})))

score = Score(
    id="score-1",
    objective="Build a feature",
    tasks=(
        Task(id="plan", instruction="Plan the work", capability=Capability.PLAN),
        Task(
            id="code",
            instruction="Implement it",
            capability=Capability.CODE,
            depends_on=("plan",),
        ),
    ),
)

context = Conductor(CapabilityRouter(registry)).perform(score)
print(context.trace)
```

## Philosophy

Every AI has strengths. Beethoven does not ask every model to do everything. It
asks each model, agent, or tool to perform the part it plays best.

That is the difference between an agent framework and an orchestration platform:
the platform is designed for new soloists to appear without changing the score.

## Architecture

Core layers:

- **Intent**: understand the objective, constraints, risk, privacy, and budget.
- **Score**: produce an inspectable and replayable execution plan.
- **Routing**: select soloists by capability, cost, quality, latency, and policy.
- **Execution**: run models, tools, agents, or distributed workers.
- **Critic**: review intermediate and final outputs.
- **Validation**: run tests, lint, security checks, and domain-specific proof.
- **Memory**: externalize project knowledge and semantic cache.
- **Governance**: provide approvals, permissions, traces, and observability.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for more detail.
See [docs/PRODUCT_INTERFACE.md](docs/PRODUCT_INTERFACE.md) for the desktop and
CLI product direction.

## Desktop Prototype

The first desktop workbench prototype lives in `desktop/`. It is a static shell
that captures the target product shape: project sidebar, Chat/Cowork/Code modes,
conversation canvas, score inspector, execution trace, permission controls, and
composer. The sidebar actions for new tasks, session search, and skills are
live when served through the local API. The composer can attach workspace files
as `@path` context and preview a score before running it, mirroring
`beethoven workspace files` and `beethoven score`. The desktop `/ commands`
surface is a helper palette, not the terminal CLI itself. The real terminal
workbench is `beethoven chat`, which runs independently in a shell. The top-bar
session menu can copy score IDs, insert session commands, and export the current
score JSON.

Open it directly, or serve it through Beethoven's local desktop API:

```bash
beethoven desktop
beethoven desktop --open
```

Then visit `http://localhost:4173`.

A first Tauri v2 shell is also available for native desktop development:

```bash
npm install
npm run tauri:dev
```

See [docs/DESKTOP_PACKAGING.md](docs/DESKTOP_PACKAGING.md).

## Supported Soloist Targets

Planned adapters include:

- Ollama
- Claude
- Codex
- OpenAI
- Gemini
- Mistral
- OpenRouter
- LiteLLM-compatible providers
- local CLI tools
- remote workers
- plugin-defined agents

## Roadmap

- **Phase I: Solo** - stable score model, conductor, registry, router, CLI.
- **Phase II: Ensemble** - provider adapters, validation hooks, semantic cache.
- **Phase III: Orchestra** - parallel execution, critic loops, policy routing.
- **Phase IV: Philharmonic** - plugin SDK, marketplace, hybrid local/cloud
  execution, dashboard, distributed runs.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Try the CLI:

```bash
beethoven chat
beethoven score "Refactor this repository"
beethoven run "Refactor this repository"
beethoven run "Refactor this repository" --json
beethoven run "Review @README.md" --soloist ollama
beethoven run "Review @README.md" --validate "python -m pytest"
beethoven desktop
beethoven desktop --open
beethoven sessions list
beethoven sessions show <session-id>
beethoven soloists list
beethoven skills list
beethoven workspace
beethoven workspace files
beethoven package sidecar
```

Inside `beethoven chat`, type an objective to run it directly, or use slash
commands such as `/score`, `/run`, `/files`, `/workspace`, `/permission`,
`/effort`, `/soloist`, and `/exit`.

Without installing dev dependencies, the current tests can also run with:

```bash
PYTHONPATH=src python -m pytest
```

## License

MIT
