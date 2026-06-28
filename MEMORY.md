# Beethoven Memory

Last updated: 2026-06-28

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
- deterministic score planning;
- dependency-aware execution;
- JSON serialization;
- a CLI;
- a local desktop HTTP API;
- a static desktop workbench;
- session history;
- workspace and Git context;
- workspace file discovery;
- a Tauri v2 desktop shell scaffold;
- tests for core execution, CLI, and desktop API.

## Core Runtime

Important modules:

- `src/beethoven/core.py`: core contracts: `Capability`, `TaskStatus`, `Task`,
  `Score`, `ExecutionContext`, `SoloistResult`, `Soloist`.
- `src/beethoven/conductor.py`: `Conductor` executes tasks in dependency order
  and records trace/status/artifacts.
- `src/beethoven/routing.py`: `SoloistRegistry` and `CapabilityRouter`.
- `src/beethoven/planning.py`: deterministic baseline score generator.
- `src/beethoven/soloists.py`: `EchoSoloist`, the offline deterministic worker.
- `src/beethoven/runtime.py`: shared runtime helpers for CLI and desktop:
  `score_objective`, `run_objective`, `list_soloists`, `list_skills`.
- `src/beethoven/serialization.py`: `score_to_dict` and `context_to_dict`.
- `src/beethoven/desktop_state.py`: local JSON-backed session store.
- `src/beethoven/workspace.py`: Git/workspace inspection and attachable file
  listing.
- `src/beethoven/packaging.py`: sidecar launcher generation.

Current baseline score tasks:

1. `understand` with capability `analyze`.
2. `plan` with capability `plan`, depends on `understand`.
3. `synthesize` with capability `synthesize`, depends on `plan`.

Current available soloist:

- `local-echo`: deterministic local/offline soloist used for testing and UI
  flows.

Planned soloist catalog:

- `ollama`;
- `openai-compatible`;
- `codex`.

## CLI Surface

Implemented commands:

```bash
beethoven chat
beethoven score "<objective>"
beethoven score "<objective>" --json
beethoven run "<objective>"
beethoven run "<objective>" --json
beethoven run "<objective>" --soloist local-echo --permission ask --effort medium
beethoven desktop
beethoven desktop --open
beethoven sessions list
beethoven sessions list --json
beethoven sessions show <session-id>
beethoven sessions show <session-id> --json
beethoven soloists list
beethoven soloists list --json
beethoven skills list
beethoven skills list --json
beethoven workspace
beethoven workspace --json
beethoven workspace files
beethoven workspace files --json
beethoven workspace files --limit 20
beethoven package sidecar
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
- `GET /api/skills`;
- `GET /api/workspace`;
- `GET /api/files`;
- `POST /api/score`;
- `POST /api/run`.

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
- score preview through `/api/score`;
- run through `/api/run`;
- score inspector and progress timeline;
- workspace/Git context through `/api/workspace`;
- attachable context files through `/api/files`, inserted as `@path`;
- filterable `/ commands` palette that inserts CLI commands into composer;
- skills panel from `/api/skills`;
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

This writes `src-tauri/bin/beethoven-sidecar`.

Packaging is not production-complete. A bundled Python sidecar/runtime strategy
is still needed before real installers.

## Tests And Validation

Current test suite:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

Latest known status after the current implementation:

- `12 passed`;
- Ruff passes.

Test coverage currently includes:

- score JSON CLI;
- run CLI trace and controls;
- desktop command registration;
- session list/show;
- soloist catalog;
- skills catalog;
- workspace command;
- workspace files command;
- sidecar launcher generation;
- desktop API health, soloists, skills, workspace, files, run, sessions, detail;
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
- mobile 390px no horizontal overflow.

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

- No real model/provider adapter yet.
- The terminal CLI is line-oriented, not a full-screen TUI like OpenCode yet.
- `soloist`, `permission_mode`, and `effort` are recorded but not deeply enforced
  beyond metadata/routing scaffolding.
- No true file content ingestion yet; files are attached as `@path` references.
- No streaming run output yet.
- No diff, patch, approval, or test execution workflow yet.
- No persistent conversation message history beyond saved run/session summaries.
- No plugin SDK.
- No real automation/scheduled scores.
- No production desktop installer.
- No OpenAI/Ollama/Codex adapter implementation.
- No semantic memory/cache layer.
- No security policy sandbox beyond the current local prototype assumptions.

## Recommended Next Plan

### 1. Add A Real Soloist Adapter Boundary

Goal: move from `local-echo` only to a real adapter architecture without
hard-coding one provider.

Suggested steps:

- Define a provider adapter interface or extend the `Soloist` contract with
  config/availability metadata.
- Add an `OpenAICompatibleSoloist` or `OllamaSoloist` behind environment
  variables/config.
- Keep `local-echo` as fallback.
- Expose adapter availability in `beethoven soloists list` and `/api/soloists`.
- Add tests that do not require network/API keys.

### 2. Make Context Attachments Semantically Useful

Goal: attached `@path` files should influence scoring/runs.

Suggested steps:

- Parse `@path` references from composer objective.
- Add selected file paths to score metadata.
- Add a safe file reader with size limits and ignored paths.
- Show attached files in the score inspector.
- Add CLI parity, for example:

```bash
beethoven run "Review @README.md"
```

### 3. Add Run Streaming And Event Trace

Goal: desktop should feel alive during execution, closer to Codex/Claude/ZCode.

Suggested steps:

- Introduce a run event model: task started, routed, artifact produced, task
  completed, run completed.
- Add an API endpoint for event polling or Server-Sent Events.
- Update the timeline progressively instead of after the whole run.
- Keep CLI output compatible with streaming or verbose mode.

### 4. Add Validation Hooks

Goal: turn Beethoven from planner/executor into a trustworthy coding workflow.

Suggested steps:

- Define validation tasks/capabilities.
- Add a local command validator that can run configured commands.
- Add CLI options such as `--validate`.
- Surface validation status in desktop inspector.

### 5. Strengthen Native Desktop Packaging

Goal: make the Tauri shell closer to a usable app.

Suggested steps:

- Generate and wire app icons.
- Decide production sidecar strategy.
- Ensure Tauri dev/build works on a clean machine.
- Add packaging documentation for macOS first.

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

Run Tauri dev:

```bash
npm run tauri:dev
```

Push:

```bash
git push origin main
```
