# Beethoven Memory

Last updated: 2026-07-01

## Vision

Beethoven is intended to become a universal AI orchestration platform: a
conductor that turns user intent into a portable score, routes each task to the
right soloist, records traceable execution, and exposes the same loop through a
desktop workbench and a CLI.

The product direction is intentionally close to Codex Desktop, Claude Desktop,
and ZCode Desktop:

- project-first desktop shell;
- conversation plus execution;
- visible score, trace, task state, soloist choice, permissions, and effort;
- scriptable CLI parity for every important desktop action;
- a real terminal-first CLI, not only a command palette inside the desktop;
- local-first foundation that can later host cloud, local, agent, and tool
  soloists.

## Current State

The repo is on `main` and tracks `origin/main` at
`https://github.com/ROSITO/Beethoven.git`.

The foundation is pre-alpha but executable. It includes:

- a Python orchestration kernel;
- a local echo soloist;
- a first Ollama soloist adapter when the configured local model is available;
- an execution-side OpenAI-compatible soloist adapter for SoloMLX, LiteLLM,
  OpenRouter, OpenAI-compatible local servers, and cloud `/v1` APIs;
- deterministic score planning;
- dependency-aware execution;
- run event emission from the conductor;
- JSON serialization;
- a CLI;
- a local desktop HTTP API;
- a static desktop workbench;
- session history;
- workspace and Git context;
- workspace file discovery and safe `@path` file attachment reads with binary
  blocking, MIME/size/snippet metadata, total byte budget, and bounded directory
  bundles;
- bounded Git diff inspection through CLI, desktop API, and desktop session
  menu;
- approval-token gated patch check/apply helpers through CLI, desktop API, and
  desktop patch panel;
- governed validation commands appended as explicit `validate` score tasks, with
  a policy gate that blocks mutating or unknown commands unless permission mode
  is `auto` or the exact command is explicitly approved for that run;
- desktop approve-and-rerun action for blocked validation commands;
- named validation profiles (`desktop`, `lint`, `tests`, `full`) selectable from
  CLI, desktop API, and the composer;
- RecursiveMAS-inspired recursive score strategies;
- a Tauri v2 desktop shell scaffold;
- tests for core execution, CLI, and desktop API.

## Core Runtime

Important modules:

- `src/beethoven/core.py`: core contracts: `Capability`, `TaskStatus`, `Task`,
  `Score`, `ExecutionContext`, `SoloistResult`, `Soloist`.
- `src/beethoven/conductor.py`: `Conductor` executes tasks in dependency order,
  records trace/status/artifacts, and emits run events through `event_sink`.
- `src/beethoven/routing.py`: `SoloistRegistry` and `CapabilityRouter`, with
  task-level and requested soloist selection when the target can satisfy the
  task.
- `src/beethoven/planning.py`: deterministic baseline score generator and
  normalized JSON score ingestion for the hidden orchestrator.
- `src/beethoven/orchestrator.py`: Beethoven's hidden local planning model
  boundary. It auto-detects SoloMLX-server/OpenAI-compatible `/v1` first, then
  Ollama, and is not exposed as a selectable soloist. Its default profile is
  `ministral-recursivemas-router`, with routing rules for local-first planning
  and RecursiveMAS delegation.
- `src/beethoven/solomlx.py`: managed `ROSITO/SoloMLX-server` runtime brick.
  Beethoven can clone/install it into `BEETHOVEN_HOME`, start/stop the
  `mlxserve` server, prepare the default Ministral orchestration model, inspect
  `/v1/models`, and run an explicit `ensure` flow through `SoloMLXRuntime`.
  Planning can call this brick before checking the hidden conductor; by default
  it inspects only, while `BEETHOVEN_SOLOMLX_AUTOSTART=1` permits starting an
  already installed runtime.
- `src/beethoven/recursive.py`: RecursiveMAS-inspired score strategies that
  express sequential, deliberation, mixture, and distillation patterns as
  portable Beethoven tasks.
- `src/beethoven/soloists.py`: `EchoSoloist`, the offline deterministic worker,
  `OpenAICompatibleSoloist`, `OllamaSoloist`, local CLI adapters, and
  `RecursiveMASSoloist`, the optional JSON sidecar adapter.
- `src/beethoven/runtime.py`: shared runtime helpers for CLI and desktop:
  `score_objective`, `run_objective`, `list_soloists`, `list_skills`,
  `check_orchestrator`.
- `src/beethoven/serialization.py`: `score_to_dict` and `context_to_dict`.
- `src/beethoven/events.py`: event reconstruction for non-streaming clients.
- `src/beethoven/validation.py`: local validation command hooks and named
  validation profiles.
- `src/beethoven/desktop_state.py`: local JSON-backed session store.
- `src/beethoven/workspace.py`: Git/workspace inspection, attachable file
  listing, and safe attachment packing.
- `src/beethoven/packaging.py`: sidecar launcher generation. The generated
  launcher resolves `BEETHOVEN_BIN`, `beethoven`, `BEETHOVEN_PYTHON`, local
  `.venv/bin/python`, then `python3 -m beethoven.cli`.

Current baseline score tasks:

1. `understand` with capability `analyze`.
2. `plan` with capability `plan`, depends on `understand`.
3. `synthesize` with capability `synthesize`, depends on `plan`.

When `BEETHOVEN_DYNAMIC_PLANNING` is enabled, Beethoven first tries its hidden
local orchestrator. The user can choose execution soloists, but not the
orchestrator. The task list may differ, and tasks may carry a validated
`preferred_soloist` routing hint. Beethoven still enforces valid capabilities,
unique task IDs, dependency order, a maximum of six tasks, and a final synthesize
task.

Recursive strategy scores are selected explicitly with `strategy=recursive`.
They do not require the external RecursiveMAS runtime. Instead, Beethoven turns
recursive collaboration patterns into visible `Score` tasks:

- `sequential`: decompose, execute round(s), synthesize.
- `deliberation`: frame, propose, critique, revise, validate, synthesize.
- `mixture`: route experts, produce expert views, aggregate, synthesize.
- `distillation`: expert solution, distill round(s), synthesize.

This is the first integration layer for RecursiveMAS: stable score/event
contracts first, optional latent RecursiveMAS sidecar later.

Current available soloists:

- `local-echo`: deterministic local/offline soloist used for testing and UI
  flows.
- `local-reader`: safe local text reader for attached workspace files without a
  model call.
- `claude-cli`: Claude Code CLI adapter when `claude` is installed/logged in;
  invoked only when explicitly selected.
- `codex-cli`: Codex CLI adapter when `codex` is installed/logged in; invoked
  only when explicitly selected and run in read-only sandbox mode.
- `ollama`: detected when `ollama list` contains the configured model
  (`BEETHOVEN_OLLAMA_MODEL`, default `qwen3-coder:latest`), but disabled by
  default unless `BEETHOVEN_ENABLE_OLLAMA=1` is set. This is deliberate because
  large local models can create heavy memory pressure.
- `openai-compatible`: execution soloist for `/v1/chat/completions` APIs. It is
  available when `BEETHOVEN_OPENAI_COMPAT_BASE_URL`/`OPENAI_BASE_URL` or the
  persisted config points to a reachable endpoint. It can reuse SoloMLX,
  LiteLLM, OpenRouter, OpenAI-compatible local servers, or cloud APIs.
- `recursivemas`: optional RecursiveMAS backend sidecar. It becomes available
  when `BEETHOVEN_RECURSIVEMAS_COMMAND` points to an executable command that
  speaks the `beethoven.recursivemas.v1` JSON stdin/stdout protocol.

Planned soloist catalog:

- `codex`.

## CLI Surface

Implemented commands:

```bash
beethoven chat
beethoven score "<objective>"
beethoven score "<objective>" --json
beethoven score "<objective>" --strategy recursive --recursive-style deliberation --recursive-rounds 2
beethoven run "<objective>"
beethoven run "<objective>" --json
beethoven run "<objective>" --soloist local-echo --permission ask --effort medium
beethoven run "<objective>" --strategy recursive --recursive-style sequential --recursive-rounds 1
BEETHOVEN_RECURSIVEMAS_COMMAND="python3 /path/to/bridge.py" beethoven run "<objective>" --soloist recursivemas --strategy recursive
beethoven soloists configure recursivemas --command "python3 /path/to/bridge.py"
beethoven run "Review @README.md" --soloist local-reader
beethoven run "Review @README.md" --soloist claude-cli
beethoven run "Review @README.md" --soloist codex-cli
beethoven run "<objective>" --validate "python -m pytest"
beethoven run "<objective>" --validation-profile desktop
beethoven run "<objective>" --validation-profile full
beethoven desktop
beethoven desktop --open
beethoven sessions list
beethoven sessions list --json
beethoven sessions show <session-id>
beethoven sessions show <session-id> --json
beethoven soloists list
beethoven soloists list --json
beethoven soloists configure recursivemas --command "python3 /path/to/bridge.py"
beethoven soloists show recursivemas
beethoven soloists clear recursivemas
beethoven soloists check recursivemas
beethoven soloists check recursivemas --json
beethoven soloists configure openai-compatible --base-url "http://127.0.0.1:8080/v1" --model "mlx-community/Ministral-3-3B-Instruct-2512-4bit"
beethoven soloists check openai-compatible
beethoven run "Summarize @README.md" --soloist openai-compatible
beethoven skills list
beethoven skills list --json
beethoven validation profiles
beethoven validation profiles --json
beethoven workspace
beethoven workspace --json
beethoven workspace files
beethoven workspace files --json
beethoven workspace files --limit 20
beethoven package sidecar
beethoven package recursivemas-bridge
```

The CLI is the parity contract for the desktop. The desktop command palette is a
helper surface only; the real terminal CLI is `beethoven chat` plus the regular
subcommands. When a desktop action becomes important, prefer giving it a
CLI/API equivalent rather than leaving it as local browser-only behavior.

`beethoven chat` starts an interactive terminal loop:

- type a plain objective to run it;
- `/run <objective>` runs an objective;
- `/score <objective>` previews a score;
- `/files [query]` lists attachable workspace files;
- `/workspace`, `/sessions`, `/soloists`, `/skills` inspect local state;
- `/permission`, `/effort`, and `/soloist` update terminal controls;
- `/strategy`, `/recursive-style`, and `/recursive-rounds` control recursive
  scoring;
- `/exit` closes the session.

## Desktop API

Run with:

```bash
beethoven desktop --host 127.0.0.1 --port 4173
```

Implemented endpoints:

- `GET /api/health`;
- `GET /api/sessions`;
- `GET /api/sessions/<id>`;
- `GET /api/soloists`;
- `GET /api/orchestrator`;
- `GET /api/solomlx`;
- `POST /api/solomlx/install`;
- `POST /api/solomlx/start`;
- `POST /api/solomlx/prepare-orchestrator`;
- `DELETE /api/solomlx`;
- `GET /api/skills`;
- `GET /api/validation-profiles`;
- `GET /api/workspace`;
- `GET /api/files`;
- `POST /api/score`;
- `POST /api/run`;
- `POST /api/run/stream` returning NDJSON run events and a final
  `run_completed` event with the full run context.
- `GET /api/soloists/<id>/check`, currently used for RecursiveMAS diagnostics.
- `GET`, `POST`, `DELETE /api/soloists/recursivemas/config` for persisted
  RecursiveMAS bridge command management.
- `GET`, `POST`, `DELETE /api/soloists/openai-compatible/config` for persisted
  OpenAI-compatible execution soloist config.

Development notes:

- Static assets live in `desktop/`.
- API and static assets are served by `src/beethoven/desktop_server.py`.
- Dev responses use `Cache-Control: no-store`.
- `BEETHOVEN_HOME` can isolate session history during tests/manual QA.

## Desktop Workbench

Files:

- `desktop/index.html`;
- `desktop/styles.css`;
- `desktop/app.js`.

Implemented UI:

- project/sidebar shell inspired by Codex, Claude, and ZCode;
- Chat/Cowork/Code segmented mode switcher;
- recent sessions loaded from `/api/sessions`;
- session restore via `/api/sessions/<id>`;
- search/filter for recent sessions;
- `New task` resets composer and score state;
- composer with permission mode, soloist selector, effort selector;
- validation profile selector in the composer, backed by
  `/api/validation-profiles`;
- strategy controls for baseline vs recursive score generation, recursive
  pattern, and rounds;
- score preview through `/api/score`;
- run through `/api/run/stream`, with live composer status updates while events
  arrive;
- validation result summary rendered as a normal assistant-side chat message
  after a run;
- score inspector and progress timeline;
- runtime board for Beethoven's hidden local orchestrator, the managed SoloMLX
  brick, and RecursiveMAS availability;
- SoloMLX controls for install, prepare Ministral, start, stop, and refresh
  status from the desktop;
- workspace/Git context through `/api/workspace`;
- attachable context files through `/api/files`, inserted as `@path`;
- score preview attachment inspector showing status, type, size, truncation,
  snippets, and blocked/missing reasons;
- filterable `/ commands` palette that inserts CLI commands into composer;
- skills panel from `/api/skills`;
- RecursiveMAS healthcheck from the skills panel through
  `/api/soloists/recursivemas/check`;
- RecursiveMAS command save/clear controls in the skills panel;
- OpenAI-compatible base URL/model/API key controls in the skills panel;
- command center showing CLI commands and Git status;
- top-bar session actions for copying score IDs, inserting session commands,
  exporting score JSON, and opening command center;
- responsive/mobile checks have been run repeatedly at 390px wide with no
  horizontal overflow.

## Desktop Packaging

Tauri v2 scaffold exists:

- `package.json`;
- `src-tauri/Cargo.toml`;
- `src-tauri/tauri.conf.json`;
- `src-tauri/src/main.rs`;
- `src-tauri/src/lib.rs`;
- `src-tauri/build.rs`.

## RecursiveMAS Integration

Current integration is two-layer:

- native recursive scores in `src/beethoven/recursive.py`, always available via
  `--strategy recursive`;
- optional `recursivemas` soloist in `src/beethoven/soloists.py`, enabled by
  `BEETHOVEN_RECURSIVEMAS_COMMAND` or persisted
  `BEETHOVEN_HOME/config.json` config.

The sidecar protocol is documented in `docs/RECURSIVEMAS.md`. Beethoven sends
one JSON payload per task with `protocol`, `task`, `score`, and prior
`artifacts`. The sidecar can reply with plain text or JSON containing `output`,
`metadata`, `tokens`, and `cost`.

Generate a bridge scaffold with:

```bash
beethoven package recursivemas-bridge --output bridges/recursivemas_beethoven_bridge.py
```

Current Tauri dev mode starts:

```bash
beethoven desktop --host 127.0.0.1 --port 4173
```

and loads:

```text
http://127.0.0.1:4173
```

Sidecar generation:

```bash
beethoven package sidecar
```

This writes `src-tauri/bin/beethoven-sidecar`, which is also versioned and
listed in `src-tauri/tauri.conf.json` as `bundle.externalBin`.

Packaging is not production-complete. A bundled hermetic Python runtime is still
needed before real installers.

Runtime audit on 2026-07-01:

- `npm install` succeeds and installs `@tauri-apps/cli@2.11.4`.
- `npm run tauri -- --version` reports `tauri-cli 2.11.4`.
- `npm run tauri:dev` is currently blocked on this machine because `cargo` is
  not installed (`cargo metadata` cannot run).
- SoloMLX status reports the managed Ministral endpoint available at
  `http://127.0.0.1:8080/v1`.

## Tests And Validation

Current test suite:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

Latest known status after the current implementation:

- `78 passed`;
- Ruff passes;
- `node --check desktop/app.js` passes.

Test coverage currently includes:

- score JSON CLI;
- recursive score JSON CLI;
- run CLI trace and controls;
- desktop command registration;
- session list/show;
- soloist catalog;
- recursive strategy execution;
- skills catalog;
- workspace command;
- workspace files command;
- sidecar launcher generation;
- RecursiveMAS bridge generation;
- desktop API health, soloists, skills, workspace, files, run, sessions, detail;
- desktop API orchestrator/SoloMLX status and mocked SoloMLX install trigger;
- OpenAI-compatible execution soloist config, healthcheck, registry routing,
  and mocked chat completion execution;
- validation profile discovery, command/profile merge behavior, policy
  approval/blocking, CLI execution, desktop API exposure, and validation
  metadata/event recording;
- workspace attachment packing with binary blocking, total byte budget,
  MIME/size/snippet metadata, directory expansion, and enriched file listing;
- bounded workspace diff inspection in CLI/API/desktop;
- patch check/apply approval token behavior;
- conductor dependency execution;
- invalid dependency rejection.

Browser QA has been done with the in-app browser for:

- desktop sidebar actions;
- session search and restore;
- skills panel;
- score preview;
- workspace file attachment;
- slash command palette;
- session action menu;
- validation profile selector populated from `/api/validation-profiles`;
- mobile 390px no horizontal overflow.

Runtime proof after adding the execution-side OpenAI-compatible soloist:

```bash
BEETHOVEN_DYNAMIC_PLANNING=0 \
BEETHOVEN_OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8080/v1 \
BEETHOVEN_OPENAI_COMPAT_MODEL=mlx-community/Ministral-3-3B-Instruct-2512-4bit \
beethoven run "réponds simplement OK" --soloist openai-compatible --json
```

This completed with trace `understand:openai-compatible`,
`plan:openai-compatible`, `synthesize:openai-compatible`.

## Decisions Already Made

- Keep the orchestration primitives small and provider-agnostic.
- Treat `Score` as the portable inspectable execution plan.
- Treat soloists as adapters for models, agents, providers, tools, and future
  workers.
- Use local deterministic behavior first so UI/CLI/API can be tested without
  provider keys or cloud cost.
- Keep desktop and CLI concepts aligned.
- Prefer local-first privacy language and explicit permission/effort controls.
- Avoid making the desktop a marketing page; it should open directly into a
  working app surface.
- Use Tauri as the first native shell, but keep Python runtime as source of
  truth for now.

## Known Gaps

- SoloMLX-server/OpenAI-compatible and Ollama can now back the hidden local
  orchestrator, the desktop can inspect/control/ensure the managed SoloMLX
  brick, and OpenAI-compatible `/v1` APIs can be configured as execution
  soloists. Persisted hidden orchestrator config UI is still missing.
- The terminal CLI is line-oriented, not a full-screen TUI like OpenCode yet.
- `soloist`, `permission_mode`, and `effort` are recorded but not deeply enforced
  beyond metadata/routing scaffolding.
- `@path` file ingestion now has richer context packing, binary detection,
  budget enforcement, directory bundles, and desktop preview inspection. Token
  estimation is still byte-based rather than model-token based.
- Desktop consumes NDJSON run events, but the visual timeline is still mostly
  rendered from final context.
- Validation hooks now become explicit `validate` score tasks and include a
  policy gate for mutating/unknown commands plus exact-command approval for
  `ask` mode. The desktop can approve blocked validation commands and rerun, but
  the approval UX is still a compact message action rather than a full modal.
- Bounded diff inspection and approval-token gated patch apply exist, including
  a compact desktop patch panel. Rich side-by-side patch review is not
  implemented yet.
- No persistent conversation message history beyond saved run/session summaries.
- No plugin SDK.
- No real automation/scheduled scores.
- No production desktop installer.
- No semantic memory/cache layer.
- No security policy sandbox beyond the current local prototype assumptions.

## Recommended Next Plan

### 1. Harden The Soloist Adapter Boundary

Goal: turn the first `OllamaSoloist` into a provider boundary that can host
Ollama, OpenAI-compatible APIs, Codex, tools, and future workers consistently.

Suggested steps:

- Keep hardening adapter metadata/config objects instead of hard-coded env reads
  in `soloists.py`.
- Add tests that mock subprocess/API calls and never require network/API keys.
- Decide how routing handles requested-but-unavailable soloists in desktop UI.
- Keep `local-echo` as deterministic fallback for tests and demos.

### 2. Upgrade Context Attachments Further

Goal: move from byte-safe context packing to model-aware context assembly.

Suggested steps:

- Estimate model-token budgets per adapter instead of bytes only.
- Add user-controlled include/exclude patterns for directory bundles.
- Add full attachment inspector drawer with copy/open actions.
- Add semantic chunking for large files instead of simple head truncation.

### 3. Make Streaming Visibly Useful

Goal: desktop should feel alive during execution, closer to Codex/Claude/ZCode.

Suggested steps:

- Render timeline rows progressively from NDJSON events.
- Add CLI verbose/stream mode that prints events as they arrive.
- Add cancellation support for active runs.
- Persist event logs with sessions, not only reconstructed final trace.

### 4. Promote Validation Into A Governed Task Graph

Goal: move beyond post-run hooks into policy-aware validation work.

Suggested steps:

- Surface stdout/stderr and pass/fail/block details in the desktop inspector.
- Refine interactive desktop permission prompts before commands that mutate the
  workspace.
- Extend the same policy model to diff/code actions.

### 5. Strengthen Native Desktop Packaging

Goal: make the Tauri shell closer to a usable app.

Suggested steps:

- Implement a Tauri startup supervisor for the Python sidecar.
- Replace the shell launcher with a bundled Python runtime sidecar.
- Generate and wire app icons and platform bundle metadata.
- Add CI checks for `npm run tauri:dev` smoke tests where Tauri is available.
- Document macOS notarization/signing expectations.

### 6. Begin Fugu-Like Orchestration Research

Goal: define how Beethoven differs from ordinary agent frameworks and moves
toward a universal orchestration layer.

Suggested steps:

- Define score schemas for multi-agent debate, tool use, critic loops, and
  validation loops.
- Add a routing policy layer: local-first, fastest, cheapest, best-quality,
  privacy-first.
- Add cost/latency/quality metadata to soloist results.
- Add replayable traces and run comparison.

## Useful Commands

Install/dev:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm install
```

Run tests:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

Run desktop:

```bash
.venv/bin/beethoven desktop --host 127.0.0.1 --port 4173
```

Run desktop with isolated history:

```bash
BEETHOVEN_HOME=$(mktemp -d) .venv/bin/beethoven desktop --host 127.0.0.1 --port 4173
```

Run with local context/model/validation:

```bash
.venv/bin/beethoven run "Review @README.md" --soloist local-reader
.venv/bin/beethoven run "Review @README.md" --soloist claude-cli
.venv/bin/beethoven run "Review @README.md" --soloist codex-cli
BEETHOVEN_ENABLE_OLLAMA=1 .venv/bin/beethoven run "Review @README.md" --soloist ollama
.venv/bin/beethoven run "Check the project" --validate ".venv/bin/python -m pytest"
```

Run Tauri dev:

```bash
npm run tauri:dev
```

Push:

```bash
git push origin main
```
