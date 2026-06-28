const defaultScoreTasks = [
  {
    id: "understand",
    capability: "analyze",
    soloist: "local-echo",
    reason: "offline capability covers early intent analysis",
    instruction: "Clarify intent, constraints, interface references, and risks."
  },
  {
    id: "plan",
    capability: "plan",
    soloist: "local-echo",
    reason: "deterministic planner keeps the first score inspectable",
    instruction: "Create an execution score with dependencies and validation gates."
  },
  {
    id: "synthesize",
    capability: "synthesize",
    soloist: "local-echo",
    reason: "local synthesis proves the orchestration loop without provider cost",
    instruction: "Produce the final symphony from completed artifacts."
  }
];

let scoreTasks = [...defaultScoreTasks];

const scoreList = document.querySelector("#scoreList");
const composer = document.querySelector("#composer");
const sendButton = document.querySelector("#sendButton");
const timeline = document.querySelector("#timeline");
const progressPill = document.querySelector("#progressPill");
const scoreId = document.querySelector("#scoreId");
const composerStatus = document.querySelector("#composerStatus");
const sessionList = document.querySelector("#sessionList");
const newTaskButton = document.querySelector("#newTaskButton");
const searchButton = document.querySelector("#searchButton");
const skillsButton = document.querySelector("#skillsButton");
const sessionFilterButton = document.querySelector("#sessionFilterButton");
const sessionSearch = document.querySelector("#sessionSearch");
const modeTabs = [...document.querySelectorAll(".mode-tab")];
const modeEyebrow = document.querySelector("#modeEyebrow");
const modeSummary = document.querySelector("#modeSummary");
const modeConductor = document.querySelector("#modeConductor");
const soloistSelect = document.querySelector("#soloistSelect");
const permissionSelect = document.querySelector("#permissionSelect");
const effortSelect = document.querySelector("#effortSelect");
const workspaceName = document.querySelector("#workspaceName");
const workspaceBranch = document.querySelector("#workspaceBranch");
const composerWorkspaceName = document.querySelector("#composerWorkspaceName");
const composerBranch = document.querySelector("#composerBranch");
const workspaceChanges = document.querySelector("#workspaceChanges");
const terminalButton = document.querySelector("#terminalButton");
const runScoreButton = document.querySelector("#runScoreButton");
const attachFilesButton = document.querySelector("#attachFilesButton");
const slashCommandsButton = document.querySelector("#slashCommandsButton");
const scorePreviewButton = document.querySelector("#scorePreviewButton");
const commandPanel = document.querySelector("#commandPanel");
const closeCommandPanel = document.querySelector("#closeCommandPanel");
const commandSearch = document.querySelector("#commandSearch");
const commandList = document.querySelector("#commandList");
const workspaceStatusList = document.querySelector("#workspaceStatusList");
const skillsPanel = document.querySelector("#skillsPanel");
const closeSkillsPanel = document.querySelector("#closeSkillsPanel");
const skillsGrid = document.querySelector("#skillsGrid");
const scorePanel = document.querySelector("#scorePanel");
const closeScorePanel = document.querySelector("#closeScorePanel");
const scorePreviewMeta = document.querySelector("#scorePreviewMeta");
const scorePreviewList = document.querySelector("#scorePreviewList");
const filesPanel = document.querySelector("#filesPanel");
const closeFilesPanel = document.querySelector("#closeFilesPanel");
const filesPanelMeta = document.querySelector("#filesPanelMeta");
const fileSearch = document.querySelector("#fileSearch");
const fileList = document.querySelector("#fileList");

let currentWorkspace = null;
let allSessions = [];
let activeSessionId = null;
let allSkills = [];
let allFiles = [];

const modeCopy = {
  chat: {
    eyebrow: "Chat",
    summary: "Explore an idea, ask questions, and turn intent into a score.",
    conductor: "Chat mode keeps the orchestration transparent while Beethoven clarifies the user objective.",
    placeholder: "Ask Beethoven anything, @ add files, / commands, # related score"
  },
  cowork: {
    eyebrow: "Cowork",
    summary: "Work with Beethoven step by step, with approvals and visible progress.",
    conductor: "Cowork mode emphasizes plans, checkpoints, approval gates, and reversible actions.",
    placeholder: "Describe the next collaborative step, approval, or checkpoint"
  },
  code: {
    eyebrow: "Code",
    summary:
      "Build a Beethoven interface close to Codex Desktop, Claude Desktop, ZCode Desktop, with a real CLI surface.",
    conductor:
      "I created a portable score, routed it through the local echo soloist, and exposed the same loop through the CLI. The desktop workbench now mirrors that orchestration model.",
    placeholder: "Ask Beethoven anything, @ add files, / commands, # related score"
  }
};

const cliCommands = [
  {
    command: "beethoven workspace",
    description: "Inspect the current project, branch, and Git status."
  },
  {
    command: "beethoven workspace files",
    description: "List files that can be attached as composer context."
  },
  {
    command: "beethoven run \"<objective>\" --permission ask --effort medium",
    description: "Run the same orchestration loop as the composer."
  },
  {
    command: "beethoven sessions list",
    description: "List recent desktop runs."
  },
  {
    command: "beethoven soloists list",
    description: "Show available and planned soloists."
  },
  {
    command: "beethoven skills list",
    description: "Inspect routable orchestration capabilities."
  },
  {
    command: "beethoven desktop --open",
    description: "Start the local workbench."
  }
];

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderScore() {
  scoreList.innerHTML = scoreTasks
    .map(
      (task) => {
        const status = task.status ?? "done";
        const statusClass = status === "completed" ? "success" : "neutral";
        return `
        <article class="score-card">
          <header>
            <h3>${task.id}</h3>
            <span class="pill ${statusClass}">${status}</span>
          </header>
          <p>${task.instruction}</p>
          <div class="route-reason">${task.capability} → ${task.soloist}: ${task.reason}</div>
        </article>
      `;
      }
    )
    .join("");

  timeline.innerHTML = scoreTasks
    .map(
      (task, index) => `
        <li>
          <span class="step-index">${index + 1}</span>
          <div>
            <strong>${titleCase(task.id)}</strong>
            <p>${task.instruction}</p>
          </div>
          <span class="step-state">${task.status ?? "done"}</span>
        </li>
      `
    )
    .join("");

  const completed = scoreTasks.filter((task) => (task.status ?? "done") === "completed").length;
  progressPill.textContent =
    completed > 0 ? `${completed} tasks completed` : `${scoreTasks.length} tasks ready`;
}

function renderSessions(sessions) {
  if (!sessions.length) {
    sessionList.innerHTML = sessionSearch.value.trim()
      ? '<div class="session-empty">No matching sessions</div>'
      : '<div class="session-empty">No runs yet</div>';
    return;
  }

  sessionList.innerHTML = sessions
    .map((session, index) => {
      const recency = session.id === allSessions[0]?.id ? "now" : session.branch ?? "main";
      const isActive = session.id === activeSessionId;
      const activeClass = isActive ? " active" : "";
      const runningClass = isActive ? " running" : "";
      return `
        <button class="session-row${activeClass}" type="button" data-session-id="${escapeHtml(session.id)}">
          <span class="status-dot${runningClass}"></span>
          ${escapeHtml(session.title)}
          <span class="row-meta">${escapeHtml(recency)}</span>
        </button>
      `;
    })
    .join("");
}

function filterSessions(sessions, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return sessions;
  }
  return sessions.filter((session) => {
    const searchable = [
      session.title,
      session.objective,
      session.project,
      session.branch,
      session.id
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return searchable.includes(normalized);
  });
}

function renderFilteredSessions() {
  renderSessions(filterSessions(allSessions, sessionSearch.value));
}

function setSearchOpen(open) {
  sessionSearch.hidden = !open;
  searchButton.classList.toggle("active", open || Boolean(sessionSearch.value.trim()));
  if (open) {
    sessionSearch.focus();
  }
}

function applyRunContext(context) {
  scoreTasks = context.score.tasks.map((task) => taskFromApi(task, context));
  scoreId.textContent = context.score.id;
  if (context.score.metadata?.soloist) {
    soloistSelect.value = context.score.metadata.soloist;
  }
  if (context.score.metadata?.permission_mode) {
    permissionSelect.value = context.score.metadata.permission_mode;
  }
  if (context.score.metadata?.effort) {
    effortSelect.value = context.score.metadata.effort;
  }
  renderScore();
}

function renderSoloists(soloists) {
  const available = soloists.filter((soloist) => soloist.status === "available");
  const planned = soloists.filter((soloist) => soloist.status !== "available");
  const options = [
    ...available.map(
      (soloist) => `<option value="${soloist.id}">${soloist.name}</option>`
    ),
    ...planned.map(
      (soloist) => `<option value="${soloist.id}" disabled>${soloist.name} (${soloist.status})</option>`
    )
  ];
  soloistSelect.innerHTML = options.join("");
}

function renderSkills(skills) {
  if (!skills.length) {
    skillsGrid.innerHTML = '<div class="session-empty">No skills found</div>';
    return;
  }

  skillsGrid.innerHTML = skills
    .map((skill) => {
      const soloists = skill.soloists ?? [];
      const soloistNames = soloists
        .map((soloist) => `${soloist.name} · ${soloist.status}`)
        .join(", ");
      const statusClass = skill.status === "available" ? "success" : "neutral";
      return `
        <article class="skill-card">
          <header>
            <h3>${escapeHtml(skill.name)}</h3>
            <span class="pill ${statusClass}">${escapeHtml(skill.status)}</span>
          </header>
          <p>${escapeHtml(skill.description)}</p>
          <div class="route-reason">${escapeHtml(soloistNames)}</div>
        </article>
      `;
    })
    .join("");
}

function renderScorePreview(score) {
  scorePreviewMeta.textContent = `${score.id} · ${score.tasks.length} planned tasks`;
  scorePreviewList.innerHTML = score.tasks
    .map(
      (task, index) => `
        <article class="preview-score-card">
          <span class="step-index">${index + 1}</span>
          <div>
            <header>
              <h3>${escapeHtml(task.id)}</h3>
              <span class="pill neutral">${escapeHtml(task.capability)}</span>
            </header>
            <p>${escapeHtml(task.instruction)}</p>
            <div class="route-reason">depends on ${escapeHtml((task.depends_on ?? []).join(", ") || "none")}</div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderFiles(files) {
  if (!files.length) {
    fileList.innerHTML = '<div class="session-empty">No matching files</div>';
    return;
  }

  fileList.innerHTML = files
    .map(
      (file) => `
        <button class="file-row" type="button" data-file-path="${escapeHtml(file.path)}">
          <span class="file-extension">${escapeHtml(file.extension)}</span>
          <span>${escapeHtml(file.path)}</span>
        </button>
      `
    )
    .join("");
}

function filterFiles(files, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return files;
  }
  return files.filter((file) => file.path.toLowerCase().includes(normalized));
}

function renderFilteredFiles() {
  renderFiles(filterFiles(allFiles, fileSearch.value));
}

function setMode(mode) {
  const copy = modeCopy[mode] ?? modeCopy.code;
  modeTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  modeEyebrow.textContent = copy.eyebrow;
  modeSummary.textContent = copy.summary;
  modeConductor.textContent = copy.conductor;
  composer.placeholder = copy.placeholder;
}

function renderWorkspace(workspace) {
  currentWorkspace = workspace;
  workspaceName.textContent = workspace.name;
  composerWorkspaceName.textContent = workspace.name;
  const branch = workspace.branch ?? "no git";
  workspaceBranch.textContent = branch;
  composerBranch.textContent = branch;
  workspaceChanges.textContent = workspace.dirty ? `${workspace.changes} changes` : "clean";
  workspaceChanges.classList.toggle("warning", Boolean(workspace.dirty));
  renderWorkspaceStatus(workspace);
}

function filterCommands(commands, query) {
  const normalized = query.trim().replace(/^\/+/, "").toLowerCase();
  if (!normalized) {
    return commands;
  }
  return commands.filter((item) => {
    const searchable = `${item.command} ${item.description}`.toLowerCase();
    return searchable.includes(normalized);
  });
}

function renderCommandList(commands = filterCommands(cliCommands, commandSearch.value)) {
  if (!commands.length) {
    commandList.innerHTML = '<div class="session-empty">No matching commands</div>';
    return;
  }

  commandList.innerHTML = commands
    .map(
      (item) => `
        <button class="command-row" type="button" data-command="${escapeHtml(item.command)}">
          <code>${escapeHtml(item.command)}</code>
          <span>${escapeHtml(item.description)}</span>
        </button>
      `
    )
    .join("");
}

function renderWorkspaceStatus(workspace) {
  const status = workspace.status ?? [];
  if (!workspace.is_git) {
    workspaceStatusList.innerHTML = '<div class="status-row"><code>not a git repository</code><span>No Git status is available.</span></div>';
    return;
  }
  if (!status.length) {
    workspaceStatusList.innerHTML = '<div class="status-row"><code>clean</code><span>No local changes.</span></div>';
    return;
  }
  workspaceStatusList.innerHTML = status
    .slice(0, 8)
    .map(
      (line) =>
        `<div class="status-row"><code>${escapeHtml(line)}</code><span>${escapeHtml(workspace.branch ?? "no branch")}</span></div>`
    )
    .join("");
}

function toggleCommandPanel(force) {
  const shouldOpen = force ?? commandPanel.hidden;
  commandPanel.hidden = !shouldOpen;
  if (shouldOpen) {
    skillsPanel.hidden = true;
    scorePanel.hidden = true;
    filesPanel.hidden = true;
    skillsButton.classList.remove("active");
    scorePreviewButton.classList.remove("active");
    attachFilesButton.classList.remove("active");
  }
  if (shouldOpen && currentWorkspace) {
    renderWorkspaceStatus(currentWorkspace);
  }
  if (shouldOpen) {
    renderCommandList();
    commandSearch.focus();
  }
}

function toggleSkillsPanel(force) {
  const shouldOpen = force ?? skillsPanel.hidden;
  skillsPanel.hidden = !shouldOpen;
  skillsButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    commandPanel.hidden = true;
    scorePanel.hidden = true;
    filesPanel.hidden = true;
    renderSkills(allSkills);
    scorePreviewButton.classList.remove("active");
    attachFilesButton.classList.remove("active");
  }
}

function toggleScorePanel(force) {
  const shouldOpen = force ?? scorePanel.hidden;
  scorePanel.hidden = !shouldOpen;
  scorePreviewButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    commandPanel.hidden = true;
    skillsPanel.hidden = true;
    filesPanel.hidden = true;
    skillsButton.classList.remove("active");
    attachFilesButton.classList.remove("active");
  }
}

function toggleFilesPanel(force) {
  const shouldOpen = force ?? filesPanel.hidden;
  filesPanel.hidden = !shouldOpen;
  attachFilesButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    commandPanel.hidden = true;
    skillsPanel.hidden = true;
    scorePanel.hidden = true;
    skillsButton.classList.remove("active");
    scorePreviewButton.classList.remove("active");
    renderFilteredFiles();
    fileSearch.focus();
  }
}

function attachFile(path) {
  const prefix = composer.value.trim() ? " " : "";
  composer.value = `${composer.value}${prefix}@${path}`;
  composer.focus();
  composerStatus.classList.remove("error");
  composerStatus.textContent = `Attached ${path}`;
}

function insertCommand(command) {
  composer.value = command;
  composer.focus();
  composerStatus.classList.remove("error");
  composerStatus.textContent = `Inserted command: ${command}`;
}

function taskFromApi(task, context) {
  const artifact = context.artifacts?.[task.id];
  const route = context.trace?.find((item) => item.startsWith(`${task.id}:`));
  const soloist = route?.split(":")[1] ?? "local-echo";
  return {
    id: task.id,
    capability: task.capability,
    soloist,
    reason: artifact?.metadata?.mode
      ? `${artifact.metadata.mode} execution returned by Beethoven runtime`
      : "selected by the local Beethoven router",
    instruction: task.instruction,
    status: context.statuses?.[task.id] ?? "ready"
  };
}

function taskFromScore(task) {
  return {
    id: task.id,
    capability: task.capability,
    soloist: "pending",
    reason: "ready for local Beethoven routing",
    instruction: task.instruction,
    status: "ready"
  };
}

async function runComposer() {
  const value = composer.value.trim();
  if (!value) {
    composer.focus();
    return;
  }

  sendButton.textContent = "…";
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Running Beethoven locally…";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        objective: value,
        soloist: soloistSelect.value,
        permission_mode: permissionSelect.value,
        effort: effortSelect.value
      })
    });
    if (!response.ok) {
      throw new Error(`Desktop API returned ${response.status}`);
    }
    const context = await response.json();
    applyRunContext(context);
    const sessions = await fetchSessions();
    activeSessionId = context.session.id;
    allSessions = [context.session, ...sessions.filter((item) => item.id !== context.session.id)];
    renderFilteredSessions();
    sendButton.textContent = "✓";
    composerStatus.textContent = `Trace: ${context.trace.join(" → ")}`;
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent =
      "Desktop API unavailable. Start it with: beethoven desktop";
    console.error(error);
  } finally {
    setTimeout(() => {
      sendButton.textContent = "↑";
    }, 900);
  }
}

async function restoreSession(sessionId) {
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Restoring session…";
  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`);
    if (!response.ok) {
      throw new Error(`Session API returned ${response.status}`);
    }
    const payload = await response.json();
    const session = payload.session;
    if (!session.run) {
      throw new Error("Session has no run context");
    }
    applyRunContext(session.run);
    activeSessionId = sessionId;
    composer.value = session.objective ?? "";
    composerStatus.textContent = `Restored: ${session.title}`;
    renderFilteredSessions();
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent = "Unable to restore that session.";
    console.error(error);
  }
}

async function loadScoreForObjective(objective) {
  try {
    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective })
    });
    if (!response.ok) {
      return;
    }
    const score = await response.json();
    scoreTasks = score.tasks.map((task) => taskFromScore(task));
    scoreId.textContent = score.id;
  } catch {
    composerStatus.textContent = "Static preview mode. Start `beethoven desktop` for live runs.";
  } finally {
    renderScore();
  }
}

async function previewComposerScore() {
  const objective = composer.value.trim() || "new orchestration task";
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Drafting score preview…";
  try {
    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective })
    });
    if (!response.ok) {
      throw new Error(`Score API returned ${response.status}`);
    }
    const score = await response.json();
    scoreTasks = score.tasks.map((task) => taskFromScore(task));
    scoreId.textContent = score.id;
    renderScore();
    renderScorePreview(score);
    toggleScorePanel(true);
    composerStatus.textContent = `Score preview ready for: ${objective}`;
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent = "Unable to preview score. Start it with: beethoven desktop";
    console.error(error);
  }
}

async function loadInitialScore() {
  await loadScoreForObjective("desktop and CLI foundation");
}

async function fetchSessions() {
  try {
    const response = await fetch("/api/sessions");
    if (!response.ok) {
      return [];
    }
    const payload = await response.json();
    return payload.sessions ?? [];
  } catch {
    return [];
  }
}

async function loadSoloists() {
  try {
    const response = await fetch("/api/soloists");
    if (!response.ok) {
      throw new Error(`Soloists API returned ${response.status}`);
    }
    const payload = await response.json();
    renderSoloists(payload.soloists ?? []);
  } catch {
    renderSoloists([
      {
        id: "local-echo",
        name: "Local Echo",
        status: "available"
      }
    ]);
  }
}

async function loadSkills() {
  try {
    const response = await fetch("/api/skills");
    if (!response.ok) {
      throw new Error(`Skills API returned ${response.status}`);
    }
    const payload = await response.json();
    allSkills = payload.skills ?? [];
  } catch {
    allSkills = [
      {
        id: "analyze",
        name: "Analyze",
        status: "available",
        description: "Route analyze work to compatible Beethoven soloists.",
        soloists: [{ id: "local-echo", name: "Local Echo", status: "available" }]
      }
    ];
  }
  renderSkills(allSkills);
}

async function loadFiles() {
  try {
    const response = await fetch("/api/files");
    if (!response.ok) {
      throw new Error(`Files API returned ${response.status}`);
    }
    const payload = await response.json();
    allFiles = payload.files ?? [];
    filesPanelMeta.textContent = `${allFiles.length} files available in ${payload.workspace?.name ?? "workspace"}`;
  } catch {
    allFiles = [
      {
        path: "README.md",
        name: "README.md",
        extension: "md"
      }
    ];
    filesPanelMeta.textContent = "Static preview mode";
  }
  renderFilteredFiles();
}

async function loadWorkspace() {
  try {
    const response = await fetch("/api/workspace");
    if (!response.ok) {
      throw new Error(`Workspace API returned ${response.status}`);
    }
    const payload = await response.json();
    renderWorkspace(payload.workspace);
  } catch {
    renderWorkspace({
      name: "Beethoven",
      branch: "main",
      dirty: false,
      changes: 0
    });
  }
}

async function loadSessions() {
  allSessions = await fetchSessions();
  renderFilteredSessions();
}

async function startNewTask() {
  activeSessionId = null;
  composer.value = "";
  sessionSearch.value = "";
  setSearchOpen(false);
  composerStatus.classList.remove("error");
  composerStatus.textContent = "New task ready.";
  permissionSelect.value = "ask";
  effortSelect.value = "medium";
  commandPanel.hidden = true;
  skillsPanel.hidden = true;
  scorePanel.hidden = true;
  filesPanel.hidden = true;
  scorePreviewButton.classList.remove("active");
  attachFilesButton.classList.remove("active");
  document.querySelectorAll(".nav-action").forEach((button) => {
    button.classList.toggle("active", button === newTaskButton);
  });
  renderFilteredSessions();
  await loadScoreForObjective("new orchestration task");
  composer.focus();
}

composer.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    runComposer();
    return;
  }
  if (event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey) {
    setTimeout(() => {
      commandSearch.value = composer.value.trim().replace(/^\/+/, "");
      toggleCommandPanel(true);
      renderCommandList();
    }, 0);
  }
});

sendButton.addEventListener("click", runComposer);
runScoreButton.addEventListener("click", runComposer);
newTaskButton.addEventListener("click", startNewTask);
searchButton.addEventListener("click", () => setSearchOpen(sessionSearch.hidden));
skillsButton.addEventListener("click", () => toggleSkillsPanel());
sessionFilterButton.addEventListener("click", () => setSearchOpen(sessionSearch.hidden));
sessionSearch.addEventListener("input", renderFilteredSessions);
sessionSearch.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    sessionSearch.value = "";
    renderFilteredSessions();
    setSearchOpen(false);
  }
});
terminalButton.addEventListener("click", () => toggleCommandPanel());
attachFilesButton.addEventListener("click", () => toggleFilesPanel());
slashCommandsButton.addEventListener("click", () => toggleCommandPanel(true));
scorePreviewButton.addEventListener("click", previewComposerScore);
closeCommandPanel.addEventListener("click", () => toggleCommandPanel(false));
closeSkillsPanel.addEventListener("click", () => toggleSkillsPanel(false));
closeScorePanel.addEventListener("click", () => toggleScorePanel(false));
closeFilesPanel.addEventListener("click", () => toggleFilesPanel(false));
commandSearch.addEventListener("input", () => renderCommandList());
commandSearch.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    toggleCommandPanel(false);
    composer.focus();
    return;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    const [firstCommand] = filterCommands(cliCommands, commandSearch.value);
    if (firstCommand) {
      insertCommand(firstCommand.command);
      toggleCommandPanel(false);
    }
  }
});
fileSearch.addEventListener("input", renderFilteredFiles);
fileList.addEventListener("click", (event) => {
  const row = event.target.closest(".file-row");
  if (row?.dataset.filePath) {
    attachFile(row.dataset.filePath);
  }
});
commandList.addEventListener("click", (event) => {
  const row = event.target.closest(".command-row");
  if (row?.dataset.command) {
    insertCommand(row.dataset.command);
    toggleCommandPanel(false);
  }
});
sessionList.addEventListener("click", (event) => {
  const row = event.target.closest(".session-row");
  if (row?.dataset.sessionId) {
    restoreSession(row.dataset.sessionId);
  }
});
modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});
renderCommandList();
renderScore();
loadWorkspace();
loadSoloists();
loadSkills();
loadFiles();
loadSessions();
loadInitialScore();
