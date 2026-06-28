# Product Interface

Beethoven should ship as both a desktop workbench and a CLI. They must feel like
two surfaces over the same orchestration engine, not two unrelated products.

The target desktop feel is close to Codex Desktop, Claude Desktop, and ZCode
Desktop: calm, project-based, conversation-native, with visible controls for
context, permissions, model choice, and execution progress.

## Interface Principles

- **Project-first**: users work inside repositories, folders, workspaces, and
  persistent threads.
- **Conversation plus execution**: the main surface is a chat, but the product
  must show plans, traces, diffs, approvals, and validation results as first-class
  objects.
- **Transparent orchestration**: Beethoven should expose the score, selected
  soloists, routing reasons, costs, and validation status.
- **Fast mode switching**: users should move between Chat, Cowork, Code, and
  Automation without changing mental models.
- **CLI parity**: anything important in the desktop app should be scriptable.

## Desktop Layout

### Left Sidebar

The sidebar is the user's map:

- workspace/project switcher;
- new session/task button;
- search;
- skills/plugins;
- recent sessions;
- grouped projects;
- pinned threads;
- account, settings, and local/cloud status.

The active item should show recency, state, and possibly a small execution
indicator.

### Top Bar

The top bar should show:

- current project;
- current thread/session title;
- Git branch when a repository is attached;
- mode selector;
- run/progress controls;
- compact menu for export, share, archive, and settings.

### Main Canvas

The main canvas has three expected states:

- **Empty state**: large composer centered with project and branch context.
- **Conversation state**: messages, plans, tool calls, score cards, validation
  blocks, and final synthesis.
- **Execution state**: progress timeline, running tasks, selected soloists,
  artifacts, diffs, and approval gates.

### Composer

The composer is the control center:

- prompt input;
- file/context attachments;
- slash commands;
- permission mode, such as Auto, Ask before changes, or Read-only;
- model or router policy picker;
- budget/effort control;
- microphone and submit controls;
- warning banners for quota, missing credentials, risky actions, or dirty Git
  state.

## Core Views

### Chat

General orchestration conversations, planning, explanations, and synthesis.

### Cowork

Live collaborative mode where Beethoven proposes next steps, asks approvals, and
updates a persistent plan.

### Code

Repository-aware mode with diffs, tests, terminal output, branch controls,
validation gates, and commit/push actions.

### Automation

Scheduled or recurring scores: monitors, reminders, repo checks, periodic
research, and background validation.

### Score Inspector

The differentiating view. It should show:

- objective;
- tasks and dependencies;
- selected soloist for each task;
- routing reason;
- cost and token estimate;
- status;
- artifacts;
- validation result.

## CLI Shape

The CLI should mirror the desktop concepts:

```bash
beethoven score "Refactor this repository"
beethoven run "Refactor this repository"
beethoven run score.json --policy local-first
beethoven trace <run-id>
beethoven soloists list
beethoven plugins list
```

The first implemented commands are:

- `beethoven score <objective>`: create a deterministic baseline score.
- `beethoven run <objective>`: execute that score with the local echo soloist.

## First Product Milestone

MVP 0.1 should prove the loop:

1. A user enters an objective in CLI or desktop composer.
2. Beethoven creates an inspectable score.
3. Beethoven routes tasks to configured soloists.
4. Beethoven shows a trace with reasons and status.
5. Beethoven returns a final synthesis.

The desktop can start as a thin shell over the CLI/API, but the product contract
must be designed now so the CLI, API, and desktop stay aligned.
