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
- `OpenAICompatibleSoloist`: execution adapter for SoloMLX, LiteLLM,
  OpenRouter, local servers, and cloud APIs exposing `/v1/chat/completions`.
- `ClaudeCliSoloist` and `CodexCliSoloist`: CLI adapters for logged-in local
  Claude Code and Codex installations.
- Hidden local orchestrator: Beethoven can use a lightweight local model through
  SoloMLX-server/OpenAI-compatible `/v1` or Ollama to create and route scores.
- Managed SoloMLX brick: Beethoven can install, start, stop, and inspect
  `ROSITO/SoloMLX-server` as its local MLX runtime.
- `@path` attachments: safe workspace file context with binary blocking,
  MIME/size/snippet metadata, total byte budgeting, and bounded directory
  bundles.
- Run events: score/task/validation events for desktop streaming.
- Dynamic planning: Beethoven's local orchestrator proposes a task score, then
  Beethoven validates and executes the normalized plan.
- Recursive strategies: RecursiveMAS-inspired score patterns for sequential,
  deliberation, mixture, and distillation orchestration.

The first implementation is intentionally small. The foundation must stay stable
enough for future providers and plugins to attach naturally.

## Recursive Orchestration

Beethoven now includes a native recursive strategy inspired by RecursiveMAS. It
keeps the recursion inside the portable `Score` contract first, so every round
is visible in the CLI, desktop inspector, event stream, and validation trace.

Supported patterns:

- `sequential`: decompose, execute each round, synthesize.
- `deliberation`: propose, critique, revise, validate, synthesize.
- `mixture`: route expert perspectives, aggregate, synthesize.
- `distillation`: expert solution, distill rounds, synthesize.

Try it from the terminal:

```bash
beethoven score "Integrate RecursiveMAS" --strategy recursive --recursive-style deliberation --recursive-rounds 2
beethoven run "Integrate RecursiveMAS" --strategy recursive --recursive-style sequential --recursive-rounds 1
```

The external RecursiveMAS backend is represented as an experimental soloist
target. The current production-safe integration point is the recursive score
strategy; a future sidecar can implement the latent RecursiveMAS runtime behind
the same score/event contracts.

See [docs/RECURSIVEMAS.md](docs/RECURSIVEMAS.md) for the optional sidecar
protocol. When `BEETHOVEN_RECURSIVEMAS_COMMAND` is configured, the
`recursivemas` soloist becomes available:

```bash
beethoven package recursivemas-bridge --output bridges/recursivemas_beethoven_bridge.py
beethoven soloists configure recursivemas --command "python3 /path/to/bridge.py"

BEETHOVEN_RECURSIVEMAS_COMMAND="python3 /path/to/bridge.py" \
  beethoven run "Solve with RecursiveMAS" --soloist recursivemas --strategy recursive

beethoven soloists check recursivemas
```

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
See [docs/RECURSIVEMAS.md](docs/RECURSIVEMAS.md) for the RecursiveMAS sidecar
protocol.

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
beethoven run "Review @README.md" --validate "python -m pytest"
beethoven run "Review @README.md" --validation-profile desktop
beethoven run "Review @README.md" --validation-profile full
beethoven run "Review @README.md" --soloist claude-cli
beethoven run "Review @README.md" --soloist codex-cli
beethoven run "Explore RecursiveMAS" --strategy recursive --recursive-style deliberation --recursive-rounds 2
beethoven desktop
beethoven desktop --open
beethoven sessions list
beethoven sessions show <session-id>
beethoven soloists list
beethoven soloists configure recursivemas --command "python3 /path/to/bridge.py"
beethoven soloists check recursivemas
beethoven soloists configure openai-compatible --base-url "http://127.0.0.1:8080/v1" --model "mlx-community/Ministral-3-3B-Instruct-2512-4bit"
beethoven soloists check openai-compatible
beethoven run "Review @README.md" --soloist openai-compatible
beethoven orchestrator status
beethoven solomlx status
beethoven solomlx install
beethoven solomlx prepare-orchestrator
beethoven solomlx start
beethoven solomlx ensure --start
beethoven skills list
beethoven validation profiles
beethoven workspace
beethoven workspace files
beethoven package sidecar
beethoven package recursivemas-bridge
```

Inside `beethoven chat`, type an objective to run it directly, or use slash
commands such as `/score`, `/run`, `/files`, `/workspace`, `/permission`,
`/effort`, `/soloist`, `/orchestrator`, `/strategy`, `/recursive-style`,
`/recursive-rounds`, and `/exit`.

## Local Orchestrator

The orchestrator is not chosen in the UI. Beethoven owns it and uses it before
execution to decompose the objective and optionally suggest the best execution
soloist for each task. If no local orchestration model is reachable, Beethoven
falls back to the deterministic baseline score.

SoloMLX-server is the preferred local brick because it exposes an
OpenAI-compatible API and can be managed by Beethoven:

```bash
beethoven solomlx install
beethoven solomlx prepare-orchestrator
beethoven solomlx start
beethoven solomlx ensure --start
beethoven solomlx status

BEETHOVEN_ORCHESTRATOR_PROVIDER=solomlx \
BEETHOVEN_ORCHESTRATOR_BASE_URL=http://127.0.0.1:8080/v1 \
beethoven orchestrator status
```

The default orchestration model profile is:

```text
mlx-community/Ministral-3-3B-Instruct-2512-4bit
```

Beethoven starts SoloMLX with `MLXSERVE_DEFAULT_MODEL` set to that model unless
`BEETHOVEN_ORCHESTRATOR_MODEL` overrides it. The orchestrator prompt is tuned
for compact score generation, local-first routing, and RecursiveMAS delegation
when `recursivemas` is available.

During planning, Beethoven treats SoloMLX as an internal runtime dependency, not
as a user-selected soloist. By default it only inspects the managed runtime. Set
`BEETHOVEN_SOLOMLX_AUTOSTART=1` to let Beethoven start an already installed
SoloMLX server automatically before checking the hidden conductor. Set
`BEETHOVEN_SOLOMLX_AUTOPREPARE=1` only when you explicitly want Beethoven to
pull/prepare the default orchestration model as part of that ensure step.

SoloMLX downloads are isolated from the global Hugging Face cache by default:
`~/.beethoven/huggingface`. Override with `BEETHOVEN_SOLOMLX_CACHE` when needed.
Beethoven also derives SoloMLX memory guardrails from machine RAM; override with
`BEETHOVEN_SOLOMLX_MAX_MEMORY_GB` and `BEETHOVEN_SOLOMLX_HARD_MEMORY_GB`.

Ollama can also back the hidden orchestrator:

```bash
BEETHOVEN_ORCHESTRATOR_PROVIDER=ollama \
BEETHOVEN_ORCHESTRATOR_MODEL=ministral \
beethoven orchestrator status
```

`BEETHOVEN_ORCHESTRATOR_PROVIDER=auto` is the default. In auto mode Beethoven
checks SoloMLX-server only; Ollama is used for orchestration only when
`BEETHOVEN_ORCHESTRATOR_PROVIDER=ollama` or `BEETHOVEN_ENABLE_OLLAMA=1` is set,
to avoid surprise memory pressure. Set `BEETHOVEN_DYNAMIC_PLANNING=0` to force
deterministic baseline planning.

Ollama is detected but disabled by default in the app because large local models
can create heavy memory pressure. Enable it explicitly only when you are ready
to run the configured model:

```bash
BEETHOVEN_ENABLE_OLLAMA=1 beethoven run "Review @README.md" --soloist ollama
```

Claude CLI and Codex CLI are detected when installed locally. They are only
invoked when explicitly selected with `--soloist claude-cli` or
`--soloist codex-cli`; Codex runs in read-only sandbox mode from Beethoven.
They are execution soloists, not the default orchestrator.

Any OpenAI-compatible `/v1` API can also be used as an execution soloist:

```bash
beethoven soloists configure openai-compatible \
  --base-url "http://127.0.0.1:8080/v1" \
  --model "mlx-community/Ministral-3-3B-Instruct-2512-4bit"

beethoven soloists check openai-compatible
beethoven run "Summarize @README.md" --soloist openai-compatible
```

`BEETHOVEN_OPENAI_COMPAT_BASE_URL`, `BEETHOVEN_OPENAI_COMPAT_MODEL`, and
`BEETHOVEN_OPENAI_COMPAT_API_KEY` can override the persisted config. Plain
`OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_API_KEY` are also recognized.

Validation can run as ad hoc commands or named profiles:

```bash
beethoven validation profiles
beethoven run "Check the desktop" --validation-profile desktop
beethoven run "Check everything local" --validation-profile full
```

The current built-in profiles are `desktop`, `lint`, `tests`, and `full`.
Desktop runs expose the same profiles in the composer and summarize pass/fail
results as a normal assistant-side message.

Attach files directly with `@path`. Beethoven keeps reads inside the workspace,
blocks ignored/binary files, applies a total byte budget, and can expand small
directories as bounded file bundles:

```bash
beethoven score "Review @README.md" --json
beethoven score "Review @docs" --json
beethoven run "Summarize @README.md" --soloist local-reader
```

Without installing dev dependencies, the current tests can also run with:

```bash
PYTHONPATH=src python -m pytest
```

## License

MIT
