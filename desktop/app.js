let scoreTasks = [];

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
const clearSessionsButton = document.querySelector("#clearSessionsButton");
const sessionSearch = document.querySelector("#sessionSearch");
const modeTabs = [...document.querySelectorAll(".mode-tab")];
const chatThread = document.querySelector("#chatThread");
const soloistSelect = document.querySelector("#soloistSelect");
const permissionSelect = document.querySelector("#permissionSelect");
const effortSelect = document.querySelector("#effortSelect");
const validationProfileSelect = document.querySelector("#validationProfileSelect");
const validationCommandInput = document.querySelector("#validationCommandInput");
const strategySelect = document.querySelector("#strategySelect");
const recursiveStyleSelect = document.querySelector("#recursiveStyleSelect");
const recursiveRoundsSelect = document.querySelector("#recursiveRoundsSelect");
const workspaceName = document.querySelector("#workspaceName");
const workspaceBranch = document.querySelector("#workspaceBranch");
const composerWorkspaceName = document.querySelector("#composerWorkspaceName");
const composerBranch = document.querySelector("#composerBranch");
const workspaceChanges = document.querySelector("#workspaceChanges");
const pageTitle = document.querySelector("#pageTitle");
const terminalButton = document.querySelector("#terminalButton");
const runScoreButton = document.querySelector("#runScoreButton");
const moreOptionsButton = document.querySelector("#moreOptionsButton");
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
const runtimeGrid = document.querySelector("#runtimeGrid");
const refreshRuntimeButton = document.querySelector("#refreshRuntimeButton");
const ensureSoloMlxButton = document.querySelector("#ensureSoloMlxButton");
const installSoloMlxButton = document.querySelector("#installSoloMlxButton");
const prepareSoloMlxButton = document.querySelector("#prepareSoloMlxButton");
const startSoloMlxButton = document.querySelector("#startSoloMlxButton");
const stopSoloMlxButton = document.querySelector("#stopSoloMlxButton");
const checkRecursiveMasButton = document.querySelector("#checkRecursiveMasButton");
const saveRecursiveMasButton = document.querySelector("#saveRecursiveMasButton");
const clearRecursiveMasButton = document.querySelector("#clearRecursiveMasButton");
const recursiveMasCommand = document.querySelector("#recursiveMasCommand");
const openAiBaseUrl = document.querySelector("#openAiBaseUrl");
const openAiModel = document.querySelector("#openAiModel");
const openAiApiKey = document.querySelector("#openAiApiKey");
const checkOpenAiButton = document.querySelector("#checkOpenAiButton");
const saveOpenAiButton = document.querySelector("#saveOpenAiButton");
const clearOpenAiButton = document.querySelector("#clearOpenAiButton");
const soloistCheckResult = document.querySelector("#soloistCheckResult");
const scorePanel = document.querySelector("#scorePanel");
const closeScorePanel = document.querySelector("#closeScorePanel");
const scorePreviewMeta = document.querySelector("#scorePreviewMeta");
const scorePreviewList = document.querySelector("#scorePreviewList");
const filesPanel = document.querySelector("#filesPanel");
const closeFilesPanel = document.querySelector("#closeFilesPanel");
const filesPanelMeta = document.querySelector("#filesPanelMeta");
const fileSearch = document.querySelector("#fileSearch");
const fileList = document.querySelector("#fileList");
const sessionPanel = document.querySelector("#sessionPanel");
const closeSessionPanel = document.querySelector("#closeSessionPanel");
const sessionPanelMeta = document.querySelector("#sessionPanelMeta");
const copyScoreIdButton = document.querySelector("#copyScoreIdButton");
const insertSessionCommandButton = document.querySelector("#insertSessionCommandButton");
const exportScoreButton = document.querySelector("#exportScoreButton");
const inspectDiffButton = document.querySelector("#inspectDiffButton");
const openCommandsFromMenuButton = document.querySelector("#openCommandsFromMenuButton");
const openPatchPanelButton = document.querySelector("#openPatchPanelButton");
const patchPanel = document.querySelector("#patchPanel");
const closePatchPanel = document.querySelector("#closePatchPanel");
const patchInput = document.querySelector("#patchInput");
const patchApprovalToken = document.querySelector("#patchApprovalToken");
const checkPatchButton = document.querySelector("#checkPatchButton");
const applyPatchButton = document.querySelector("#applyPatchButton");
const patchResult = document.querySelector("#patchResult");
const validationPanel = document.querySelector("#validationPanel");
const closeValidationPanel = document.querySelector("#closeValidationPanel");
const validationPanelMeta = document.querySelector("#validationPanelMeta");
const validationCommandList = document.querySelector("#validationCommandList");
const cancelValidationApprovalButton = document.querySelector("#cancelValidationApprovalButton");
const approveValidationButton = document.querySelector("#approveValidationButton");
const inspectorSoloistPill = document.querySelector("#inspectorSoloistPill");
const inspectorCost = document.querySelector("#inspectorCost");
const inspectorPrivacy = document.querySelector("#inspectorPrivacy");
const inspectorStatus = document.querySelector("#inspectorStatus");

let currentWorkspace = null;
let allSessions = [];
let activeSessionId = null;
let allSkills = [];
let allFiles = [];
let currentScore = null;
let currentRunContext = null;
let chatMessages = [];
let pendingValidationApproval = null;
let runtimeStatus = {
  orchestrator: null,
  solomlx: null,
  recursivemas: null,
  packaging: null
};
let validationProfiles = [];

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
    summary: "Start from the composer, attach files, inspect scores, and route work through local soloists.",
    conductor: "Beethoven is ready to draft a score from your next objective.",
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
    command: "beethoven run \"<objective>\" --strategy recursive --recursive-style deliberation --recursive-rounds 2",
    description: "Run a RecursiveMAS-inspired multi-round Beethoven score."
  },
  {
    command: "beethoven sessions list",
    description: "List recent desktop runs."
  },
  {
    command: "beethoven sessions clear",
    description: "Clear local desktop session history."
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
  },
  {
    command: "beethoven package doctor",
    description: "Check Tauri, Cargo, and sidecar packaging prerequisites."
  }
];
const expectedBackendCapabilities = [
  "auto-routing",
  "streaming",
  "current-workspace",
  "fallback-routing",
  "local-synthesis"
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

function renderChat() {
  if (!chatMessages.length) {
    chatThread.innerHTML = '<div class="empty-chat">Start a new task from the composer below.</div>';
    return;
  }

  chatThread.innerHTML = chatMessages
    .map(
      (message, index) => `
        <article class="message ${message.role === "user" ? "user-message" : "assistant-message"}">
          <div class="message-meta">${escapeHtml(message.meta)}</div>
          <p>${escapeHtml(message.content)}</p>
          ${message.action === "approve-validation"
            ? `<button class="text-button message-action" type="button" data-chat-action="review-validation" data-message-index="${index}">Review validation</button>`
            : ""}
        </article>
      `
    )
    .join("");
}

function formatArtifactOutput(output) {
  if (typeof output === "string") {
    return output.trim();
  }
  if (output === null || output === undefined) {
    return "";
  }
  try {
    return JSON.stringify(output, null, 2);
  } catch {
    return String(output);
  }
}

function updateAssistantDraft(content, meta = "Beethoven") {
  if (!chatMessages.length || chatMessages[chatMessages.length - 1]?.role !== "assistant") {
    chatMessages.push({ role: "assistant", meta, content });
  } else {
    chatMessages[chatMessages.length - 1] = {
      ...chatMessages[chatMessages.length - 1],
      meta,
      content
    };
  }
  renderChat();
}

function setConversationForMode(mode) {
  const copy = modeCopy[mode] ?? modeCopy.code;
  composer.placeholder = copy.placeholder;
  if (!currentRunContext) {
    pageTitle.textContent = "New task";
  }
  renderChat();
}

function setConversationForRun(context) {
  chatMessages = [
    {
      role: "user",
      meta: "You",
      content: context.score.objective,
    },
    {
      role: "assistant",
      meta: soloistLabel(context),
      content: finalResponseFromContext(context),
    },
  ];
  const validationSummary = validationSummaryFromContext(context);
  if (validationSummary) {
    const blockedCommands = blockedValidationResults(context);
    pendingValidationApproval = blockedCommands.length
      ? {
          objective: context.score.objective,
          commands: blockedCommands,
        }
      : null;
    chatMessages.push({
      role: "assistant",
      meta: "Validation",
      content: validationSummary,
      action: blockedCommands.length ? "approve-validation" : "",
    });
  } else {
    pendingValidationApproval = null;
  }
  renderChat();
}

function setPendingConversation(objective, soloistName) {
  pageTitle.textContent = objective;
  chatMessages = [
    {
      role: "user",
      meta: "You",
      content: objective,
    },
    {
      role: "assistant",
      meta: soloistName,
      content: "Beethoven is running the score...",
    },
  ];
  renderChat();
}

function finalResponseFromContext(context) {
  const artifacts = context.artifacts ?? {};
  const preferred = artifacts.synthesize?.output;
  const preferredText = formatArtifactOutput(preferred);
  if (preferredText) {
    return preferredText;
  }
  const trace = [...(context.trace ?? [])].reverse();
  for (const route of trace) {
    const taskId = route.split(":")[0];
    const output = formatArtifactOutput(artifacts[taskId]?.output);
    if (output) {
      return output;
    }
  }
  return "The run completed. Inspect the score trace on the right for task artifacts.";
}

function validationSummaryFromContext(context) {
  const validation = context.artifacts?.validation;
  const results = validation?.output;
  if (!Array.isArray(results) || !results.length) {
    return "";
  }
  const passed = results.filter((result) => result?.passed).length;
  const blocked = results.filter((result) => result?.blocked).length;
  const failed = results.length - passed - blocked;
  const lines = results.map((result) => {
    const marker = result?.blocked ? "blocked" : result?.passed ? "passed" : "failed";
    const reason = result?.reason ? ` (${result.reason})` : "";
    return `${result?.command}: ${marker}${reason}`;
  });
  return [
    `${passed}/${results.length} validation commands passed${failed ? `, ${failed} failed` : ""}${blocked ? `, ${blocked} blocked` : ""}.`,
    ...lines,
  ].join("\n");
}

function blockedValidationCommands(context) {
  return blockedValidationResults(context).map((result) => String(result.command));
}

function blockedValidationResults(context) {
  const results = context.artifacts?.validation?.output;
  if (!Array.isArray(results)) {
    return [];
  }
  return results
    .filter((result) => result?.blocked && result?.command)
    .map((result) => ({
      command: String(result.command),
      reason: result.reason ? String(result.reason) : "Blocked by validation policy.",
      risk: result.risk ? String(result.risk) : "unknown",
    }));
}

function soloistLabel(context) {
  const selected = context.score.metadata?.soloist;
  if (!selected || selected === "auto") {
    return "Beethoven";
  }
  return String(selected).replaceAll("-", " ");
}

function updateInspectorState(context = null) {
  const traceSoloists = [
    ...new Set(
      (context?.trace ?? [])
        .map((item) => item.split(":")[1])
        .filter(Boolean)
    )
  ];
  const selected = context?.score?.metadata?.soloist ?? soloistSelect.value;
  const label = selected === "auto" || !selected
    ? "Beethoven Auto"
    : String(selected).replaceAll("-", " ");
  inspectorSoloistPill.textContent = traceSoloists.length
    ? traceSoloists.slice(0, 2).map((item) => item.replaceAll("-", " ")).join(" + ")
    : label;
  const cost = Object.values(context?.artifacts ?? {}).reduce(
    (total, artifact) => total + (Number(artifact?.cost) || 0),
    0
  );
  inspectorCost.textContent = `$${cost.toFixed(2)}`;
  inspectorPrivacy.textContent = selected === "auto" || selected === "local-reader" || selected === "local-echo"
    ? "Local first"
    : "Hybrid";
  const statuses = Object.values(context?.statuses ?? {});
  inspectorStatus.textContent = statuses.includes("failed")
    ? "Failed"
    : statuses.length && statuses.every((status) => status === "completed")
      ? "Completed"
      : scoreTasks.some((task) => task.status === "failed")
        ? "Failed"
        : scoreTasks.some((task) => task.status === "running")
        ? "Running"
        : "Ready";
}

function renderScore() {
  if (!scoreTasks.length) {
    scoreList.innerHTML = '<div class="session-empty">No active score yet</div>';
    timeline.innerHTML = '<li class="empty-timeline">No score drafted yet</li>';
    progressPill.textContent = "Ready";
    scoreId.textContent = currentScore?.id ?? "No active score";
    updateInspectorState();
    return;
  }

  scoreList.innerHTML = scoreTasks
    .map(
      (task) => {
        const status = task.status ?? "done";
        const statusClass = taskStatusTone(status);
        return `
        <article class="score-card">
          <header>
            <h3>${escapeHtml(task.id)}</h3>
            <span class="pill ${statusClass}">${escapeHtml(status)}</span>
          </header>
          <p>${escapeHtml(task.instruction)}</p>
          ${task.summary ? `<p class="route-reason">${escapeHtml(task.summary)}</p>` : ""}
          ${task.validationDetails ? renderValidationDetails(task.validationDetails) : ""}
          <div class="route-reason">${escapeHtml(task.capability)} → ${escapeHtml(task.soloist)}: ${escapeHtml(task.reason)}</div>
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
            <strong>${escapeHtml(titleCase(task.id))}</strong>
            <p>${escapeHtml(task.instruction)}</p>
          </div>
          <span class="step-state">${escapeHtml(task.status ?? "done")}</span>
        </li>
      `
    )
    .join("");

  const completed = scoreTasks.filter((task) => (task.status ?? "done") === "completed").length;
  progressPill.textContent =
    completed > 0 ? `${completed} tasks completed` : `${scoreTasks.length} tasks ready`;
  updateInspectorState(currentRunContext);
}

function taskStatusTone(status) {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "blocked") {
    return "warning";
  }
  if (status === "running" || status === "produced") {
    return "info";
  }
  return "neutral";
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
  pageTitle.textContent = context.score.objective;
  currentScore = context.score;
  currentRunContext = context;
  if (context.score.metadata?.soloist && [...soloistSelect.options].some((option) => option.value === context.score.metadata.soloist)) {
    soloistSelect.value = context.score.metadata.soloist;
  }
  if (context.score.metadata?.permission_mode) {
    permissionSelect.value = context.score.metadata.permission_mode;
  }
  if (context.score.metadata?.effort) {
    effortSelect.value = context.score.metadata.effort;
  }
  if (context.score.metadata?.strategy) {
    strategySelect.value = context.score.metadata.strategy;
  }
  if (context.score.metadata?.recursive_style) {
    recursiveStyleSelect.value = context.score.metadata.recursive_style;
  }
  if (context.score.metadata?.recursive_rounds) {
    recursiveRoundsSelect.value = String(context.score.metadata.recursive_rounds);
  }
  setConversationForRun(context);
  renderScore();
}

function renderSoloists(soloists) {
  const available = soloists.filter((soloist) => soloist.status === "available");
  const planned = soloists.filter((soloist) => soloist.status !== "available");
  const options = [
    '<option value="auto" selected>Beethoven Auto</option>',
    ...available.map(
      (soloist) => `<option value="${soloist.id}">${soloist.name}</option>`
    ),
    ...planned.map(
      (soloist) => `<option value="${soloist.id}" disabled>${soloist.name} (${soloist.status})</option>`
    )
  ];
  soloistSelect.innerHTML = options.join("");
  updateInspectorState(currentRunContext);
}

function renderValidationProfiles(profiles) {
  validationProfiles = profiles;
  const options = [
    '<option value="none">No validation</option>',
    ...profiles.map(
      (profile) =>
        `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.name)}</option>`
    )
  ];
  validationProfileSelect.innerHTML = options.join("");
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

function runtimeTone(status) {
  if (status === "available" || status === "running" || status === "ready") {
    return "success";
  }
  if (status === "not_installed" || status === "stopped" || status === "planned") {
    return "neutral";
  }
  return "warning";
}

function runtimeCard({ title, status, badge, body, detail }) {
  return `
    <article class="runtime-card">
      <header>
        <h3>${escapeHtml(title)}</h3>
        <span class="pill ${runtimeTone(status)}">${escapeHtml(badge ?? status ?? "unknown")}</span>
      </header>
      <p>${escapeHtml(body ?? "No runtime status loaded yet.")}</p>
      ${detail ? `<div class="route-reason">${escapeHtml(detail)}</div>` : ""}
    </article>
  `;
}

function renderRuntimeStatus() {
  const orchestrator = runtimeStatus.orchestrator;
  const solomlx = runtimeStatus.solomlx;
  const recursivemas = runtimeStatus.recursivemas;
  const packaging = runtimeStatus.packaging;
  const solomlxModels = solomlx?.models?.length
    ? `Models: ${solomlx.models.slice(0, 2).join(", ")}`
    : solomlx?.preferred_orchestrator_model
      ? `Preferred: ${solomlx.preferred_orchestrator_model}`
      : "";
  const packagingBlockers = packaging?.blockers?.length
    ? `${packaging.blockers.length} blocker${packaging.blockers.length > 1 ? "s" : ""}: ${packaging.blockers
        .slice(0, 2)
        .map((blocker) => blocker.name)
        .join(", ")}`
    : packaging?.root;

  runtimeGrid.innerHTML = [
    runtimeCard({
      title: "Beethoven Orchestrator",
      status: orchestrator?.status,
      badge: orchestrator?.provider ?? orchestrator?.status,
      body: orchestrator?.available
        ? "Hidden local conductor is ready to draft and route scores."
        : orchestrator?.message ?? "Local conductor status is unavailable.",
      detail: orchestrator?.model
        ? `${orchestrator.profile ?? "profile"} · ${orchestrator.model}`
        : orchestrator?.base_url
    }),
    runtimeCard({
      title: "SoloMLX Runtime",
      status: solomlx?.status,
      badge: solomlx?.status,
      body: solomlx?.message ?? "SoloMLX status is unavailable.",
      detail: solomlxModels
    }),
    runtimeCard({
      title: "RecursiveMAS",
      status: recursivemas?.status,
      badge: recursivemas?.status,
      body: recursivemas?.message ?? "Optional recursive sidecar is not checked yet.",
      detail: recursivemas?.command
    }),
    runtimeCard({
      title: "Tauri Packaging",
      status: packaging?.status,
      badge: packaging?.status,
      body: packaging?.message ?? "Desktop packaging status is unavailable.",
      detail: packagingBlockers
    })
  ].join("");
}

function renderSoloistCheck(report) {
  const available = Boolean(report.available);
  soloistCheckResult.hidden = false;
  soloistCheckResult.classList.toggle("available", available);
  soloistCheckResult.classList.toggle("unavailable", !available);
  soloistCheckResult.innerHTML = `
    <strong>${escapeHtml(report.id ?? "soloist")} · ${escapeHtml(report.status ?? "unknown")}</strong>
    <p>${escapeHtml(report.message ?? "No diagnostic message returned.")}</p>
    ${report.command ? `<p><code>${escapeHtml(report.command)}</code></p>` : ""}
    ${report.output_preview ? `<p>${escapeHtml(report.output_preview)}</p>` : ""}
  `;
}

function renderRecursiveMasConfig(config) {
  recursiveMasCommand.value = config.command ?? "";
}

function renderOpenAiConfig(config) {
  openAiBaseUrl.value = config.base_url ?? "";
  openAiModel.value = config.model ?? "";
  openAiApiKey.value = "";
  openAiApiKey.placeholder = config.api_key_configured
    ? "API key configured"
    : "leave blank to keep local/no-key";
}

function renderScorePreview(score) {
  const attachments = score.metadata?.attachments ?? [];
  const attachedSummary = attachments.length
    ? ` · ${attachments.length} attached file${attachments.length === 1 ? "" : "s"}`
    : "";
  scorePreviewMeta.textContent = `${score.id} · ${score.tasks.length} planned tasks${attachedSummary}`;
  const attachmentMarkup = attachments.length
    ? `
        <article class="preview-score-card">
          <span class="step-index">↳</span>
          <div>
            <header>
              <h3>attached context</h3>
              <span class="pill success">${attachments.length}</span>
            </header>
            <div class="attachment-list">
              ${attachments.map((item) => attachmentPreview(item)).join("")}
            </div>
          </div>
        </article>
      `
    : "";
  scorePreviewList.innerHTML = attachmentMarkup + score.tasks
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

function attachmentPreview(item) {
  const statusClass = item.status === "attached" ? "success" : "warning";
  const detail = [
    item.media_type,
    item.bytes ? `${item.bytes} bytes` : item.size_bytes ? `${item.size_bytes} bytes` : "",
    item.truncated ? "truncated" : "",
    item.source_directory ? `from ${item.source_directory}` : ""
  ].filter(Boolean).join(" · ");
  return `
    <div class="attachment-preview">
      <div>
        <strong>${escapeHtml(item.path)}</strong>
        <span class="pill ${statusClass}">${escapeHtml(item.status)}</span>
      </div>
      ${detail ? `<p>${escapeHtml(detail)}</p>` : ""}
      ${item.reason ? `<p>${escapeHtml(item.reason)}</p>` : ""}
      ${item.snippet ? `<p>${escapeHtml(item.snippet)}</p>` : ""}
    </div>
  `;
}

function preferReaderForAttachedScore(score) {
  const attachments = score.metadata?.attachments ?? [];
  const hasAttachedFiles = attachments.some((item) => item.status === "attached");
  const hasLocalReader = [...soloistSelect.options].some((option) => option.value === "local-reader");
  if (hasAttachedFiles && hasLocalReader && soloistSelect.value === "local-echo") {
    soloistSelect.value = "local-reader";
  }
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
          <span>
            <strong>${escapeHtml(file.path)}</strong>
            <small>${escapeHtml(file.media_type ?? "text/plain")} · ${escapeHtml(String(file.bytes ?? 0))} bytes</small>
          </span>
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
  if (!currentRunContext) {
    setConversationForMode(mode);
  }
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

async function loadBackendHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error(`Health API returned ${response.status}`);
    }
    const health = await response.json();
    const capabilities = new Set(health.capabilities ?? []);
    const missing = expectedBackendCapabilities.filter((item) => !capabilities.has(item));
    if (missing.length) {
      composerStatus.classList.add("error");
      composerStatus.textContent = `Backend needs restart: missing ${missing.join(", ")}`;
      if (!chatMessages.length) {
        chatMessages = [
          {
            role: "assistant",
            meta: "Beethoven",
            content: "The desktop backend is running an older Beethoven build. Restart the app or server before running tasks.",
          },
        ];
        renderChat();
      }
      return;
    }
    composerStatus.classList.remove("error");
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent = "Desktop backend is unavailable. Start it with: beethoven desktop";
    console.error(error);
  }
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

function hideUtilityPanels() {
  commandPanel.hidden = true;
  skillsPanel.hidden = true;
  scorePanel.hidden = true;
  filesPanel.hidden = true;
  sessionPanel.hidden = true;
  validationPanel.hidden = true;
  skillsButton.classList.remove("active");
  scorePreviewButton.classList.remove("active");
  attachFilesButton.classList.remove("active");
  moreOptionsButton.classList.remove("active");
}

function toggleCommandPanel(force) {
  const shouldOpen = force ?? commandPanel.hidden;
  commandPanel.hidden = !shouldOpen;
  if (shouldOpen) {
    hideUtilityPanels();
    commandPanel.hidden = false;
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
    hideUtilityPanels();
    skillsPanel.hidden = false;
    skillsButton.classList.add("active");
    renderSkills(allSkills);
    loadRecursiveMasConfig();
  }
}

function toggleScorePanel(force) {
  const shouldOpen = force ?? scorePanel.hidden;
  scorePanel.hidden = !shouldOpen;
  scorePreviewButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    hideUtilityPanels();
    scorePanel.hidden = false;
    scorePreviewButton.classList.add("active");
  }
}

function toggleFilesPanel(force) {
  const shouldOpen = force ?? filesPanel.hidden;
  filesPanel.hidden = !shouldOpen;
  attachFilesButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    hideUtilityPanels();
    filesPanel.hidden = false;
    attachFilesButton.classList.add("active");
    renderFilteredFiles();
    fileSearch.focus();
  }
}

function toggleSessionPanel(force) {
  const shouldOpen = force ?? sessionPanel.hidden;
  sessionPanel.hidden = !shouldOpen;
  moreOptionsButton.classList.toggle("active", shouldOpen);
  if (shouldOpen) {
    hideUtilityPanels();
    sessionPanel.hidden = false;
    moreOptionsButton.classList.add("active");
    sessionPanelMeta.textContent = activeSessionId
      ? `Active session ${activeSessionId}`
      : `Current score ${scoreId.textContent}`;
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

async function copyText(value, label) {
  try {
    await navigator.clipboard.writeText(value);
    composerStatus.classList.remove("error");
    composerStatus.textContent = `Copied ${label}.`;
  } catch {
    composer.value = value;
    composer.focus();
    composerStatus.textContent = `Inserted ${label} into composer.`;
  }
}

function exportCurrentScore() {
  const payload = currentRunContext ?? { score: currentScore, trace: [], statuses: {} };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${scoreId.textContent}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
  composerStatus.classList.remove("error");
  composerStatus.textContent = `Exported ${scoreId.textContent}.json`;
}

function taskFromApi(task, context) {
  const artifact = context.artifacts?.[task.id];
  const route = [...(context.trace ?? [])].reverse().find((item) => item.startsWith(`${task.id}:`));
  const soloist = route?.split(":")[1] ?? "local-echo";
  const output = task.capability === "validate"
    ? validationTaskSummary(artifact?.output)
    : formatArtifactOutput(artifact?.output).slice(0, 420);
  return {
    id: task.id,
    capability: task.capability,
    soloist,
    reason: artifact?.metadata?.fallback_from
      ? `fallback from ${artifact.metadata.fallback_from}: ${artifact.metadata.mode ?? "runtime"} execution`
      : artifact?.metadata?.mode
      ? `${artifact.metadata.mode} execution returned by Beethoven runtime`
      : "selected by the local Beethoven router",
    instruction: task.instruction,
    summary: output,
    validationDetails: task.capability === "validate"
      ? validationTaskDetails(artifact?.output)
      : null,
    status: context.statuses?.[task.id] ?? "ready"
  };
}

function validationTaskSummary(results) {
  if (!Array.isArray(results) || !results.length) {
    return "";
  }
  const passed = results.filter((result) => result?.passed).length;
  const blocked = results.filter((result) => result?.blocked).length;
  const failed = results.length - passed - blocked;
  return `${passed} passed${failed ? ` · ${failed} failed` : ""}${blocked ? ` · ${blocked} blocked` : ""}`;
}

function validationTaskDetails(results) {
  if (!Array.isArray(results) || !results.length) {
    return null;
  }
  return results.map((result) => ({
    command: String(result?.command ?? "unknown command"),
    status: result?.blocked
      ? "blocked"
      : result?.passed
        ? "passed"
        : "failed",
    risk: result?.risk ? String(result.risk) : "",
    reason: result?.reason ? String(result.reason) : "",
    returncode: result?.returncode ?? null,
    stdout: result?.stdout ? String(result.stdout) : "",
    stderr: result?.stderr ? String(result.stderr) : ""
  }));
}

function renderValidationDetails(details) {
  if (!Array.isArray(details) || !details.length) {
    return "";
  }
  return `
    <div class="validation-detail-list">
      ${details.map((item) => `
        <div class="validation-detail-card ${escapeHtml(item.status)}">
          <div class="validation-detail-head">
            <strong>${escapeHtml(item.status)}</strong>
            ${item.returncode !== null ? `<span>exit ${escapeHtml(String(item.returncode))}</span>` : ""}
          </div>
          <code>${escapeHtml(item.command)}</code>
          ${item.risk ? `<p>Risk: ${escapeHtml(item.risk)}</p>` : ""}
          ${item.reason ? `<p>${escapeHtml(item.reason)}</p>` : ""}
          ${renderValidationOutput("stdout", item.stdout)}
          ${renderValidationOutput("stderr", item.stderr)}
        </div>
      `).join("")}
    </div>
  `;
}

function renderValidationOutput(label, value) {
  const cleanValue = String(value ?? "").trim();
  if (!cleanValue) {
    return "";
  }
  const preview = cleanValue.length > 700 ? `${cleanValue.slice(0, 700)}…` : cleanValue;
  return `
    <details class="validation-output">
      <summary>${escapeHtml(label)}</summary>
      <pre>${escapeHtml(preview)}</pre>
    </details>
  `;
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

function ensureLiveScore(score) {
  currentScore = score;
  scoreId.textContent = score.id ?? "active score";
  pageTitle.textContent = score.objective ?? pageTitle.textContent;
  scoreTasks = (score.tasks ?? []).map(taskFromScore);
  renderScore();
}

function updateLiveTask(taskId, patch) {
  const index = scoreTasks.findIndex((task) => task.id === taskId);
  if (index === -1) {
    return;
  }
  scoreTasks[index] = {
    ...scoreTasks[index],
    ...patch
  };
  renderScore();
}

function scoreRequestPayload(objective, approvedValidationCommands = []) {
  const selectedValidationProfile = validationProfileSelect.value;
  const validationCommand = validationCommandInput.value.trim();
  return {
    objective,
    soloist: soloistSelect.value,
    strategy: strategySelect.value,
    recursive_style: recursiveStyleSelect.value,
    recursive_rounds: Number(recursiveRoundsSelect.value),
    validation_profiles: selectedValidationProfile && selectedValidationProfile !== "none"
      ? [selectedValidationProfile]
      : [],
    validation_commands: validationCommand ? [validationCommand] : [],
    approved_validation_commands: approvedValidationCommands
  };
}

async function runComposer(options = {}) {
  const value = (options.objective ?? composer.value).trim();
  if (!value) {
    composer.focus();
    return;
  }
  if (options.objective) {
    composer.value = value;
  }

  sendButton.textContent = "…";
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Running Beethoven locally…";
  setPendingConversation(value, soloistSelect.options[soloistSelect.selectedIndex]?.text ?? "Beethoven");
  if (!options.objective) {
    composer.value = "";
  }

  try {
    const response = await fetch("/api/run/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...scoreRequestPayload(value, options.approvedValidationCommands ?? []),
        permission_mode: permissionSelect.value,
        effort: effortSelect.value
      })
    });
    if (!response.ok) {
      throw new Error(`Desktop API returned ${response.status}`);
    }
    const context = await readRunStream(response);
    applyRunContext(context);
    const sessions = await fetchSessions();
    activeSessionId = context.session.id;
    allSessions = [context.session, ...sessions.filter((item) => item.id !== context.session.id)];
    renderFilteredSessions();
    sendButton.textContent = "✓";
    composerStatus.textContent = `Trace: ${context.trace.join(" → ")}`;
  } catch (error) {
    composerStatus.classList.add("error");
    const message = error?.message ?? "Unknown desktop API error";
    composerStatus.textContent = `Desktop run failed: ${message}`;
    updateAssistantDraft(
      message.includes("Soloist requested but unavailable: auto")
        ? "The desktop backend is still running an older Beethoven runtime. Restart the app or server, then run the task again."
        : `The desktop run failed: ${message}`,
      "Beethoven"
    );
    console.error(error);
  } finally {
    setTimeout(() => {
      sendButton.textContent = "↑";
    }, 900);
  }
}

async function approveBlockedValidation() {
  if (!pendingValidationApproval?.commands?.length) {
    return;
  }
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Approving blocked validation commands…";
  toggleValidationPanel(false);
  await runComposer({
    objective: pendingValidationApproval.objective,
    approvedValidationCommands: pendingValidationApproval.commands.map((item) => item.command),
  });
}

async function readRunStream(response) {
  if (!response.body) {
    throw new Error("Streaming response is unavailable");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalContext = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      const payload = JSON.parse(line);
      const event = payload.event ?? {};
      updateRunEventStatus(event);
      if (event.type === "run_completed") {
        finalContext = event.context;
      }
      if (event.type === "run_failed") {
        throw new Error(event.error ?? "Run failed");
      }
    }
    if (done) {
      break;
    }
  }
  if (!finalContext) {
    throw new Error("Run stream ended without a final context");
  }
  return finalContext;
}

function updateRunEventStatus(event) {
  if (event.type === "score_planned" && event.score) {
    ensureLiveScore(event.score);
    composerStatus.textContent = "Score planned. Starting execution…";
    updateAssistantDraft(`Score planned with ${(event.score.tasks ?? []).length} tasks.`, "Beethoven");
    return;
  }
  if (event.type === "task_routed") {
    updateLiveTask(event.task_id, {
      soloist: event.soloist,
      reason: event.fallback_from
        ? `fallback from ${event.fallback_from}`
        : "routed by Beethoven runtime"
    });
    composerStatus.textContent = event.fallback_from
      ? `${event.task_id} fallback to ${event.soloist}`
      : `${event.task_id} routed to ${event.soloist}`;
    updateAssistantDraft(
      event.fallback_from
        ? `${event.task_id} fell back from ${event.fallback_from} to ${event.soloist}.`
        : `${event.task_id} routed to ${event.soloist}.`,
      "Beethoven"
    );
    return;
  }
  if (event.type === "task_started") {
    updateLiveTask(event.task_id, { status: "running" });
    composerStatus.textContent = `${event.task_id} running…`;
    updateAssistantDraft(`${event.task_id} is running…`, "Beethoven");
    return;
  }
  if (event.type === "artifact_produced") {
    updateLiveTask(event.task_id, { status: "produced", reason: "artifact produced by Beethoven runtime" });
    updateAssistantDraft(`${event.task_id} produced an artifact.`, "Beethoven");
    return;
  }
  if (event.type === "task_completed") {
    updateLiveTask(event.task_id, { status: event.status ?? "completed" });
    composerStatus.textContent = `${event.task_id} completed`;
    updateAssistantDraft(`${event.task_id} completed.`, "Beethoven");
    return;
  }
  if (event.type === "task_failed") {
    updateLiveTask(event.task_id, {
      status: "failed",
      reason: event.soloist ? `${event.soloist} failed` : "task failed"
    });
    composerStatus.textContent = event.soloist
      ? `${event.task_id} failed on ${event.soloist}`
      : `${event.task_id} failed`;
    updateAssistantDraft(
      event.soloist
        ? `${event.task_id} failed on ${event.soloist}; looking for a fallback.`
        : `${event.task_id} failed.`,
      "Beethoven"
    );
    return;
  }
  if (event.type === "validation_started") {
    updateLiveTask(event.task_id, { status: "running", reason: "validation commands running" });
    composerStatus.textContent = "Running validation…";
    updateAssistantDraft("Validation is running…", "Beethoven");
    return;
  }
  if (event.type === "validation_blocked") {
    updateLiveTask(event.task_id, { status: "blocked", reason: "blocked by permission policy" });
    composerStatus.textContent = "Validation blocked by permission policy.";
    updateAssistantDraft("Validation is blocked by the current permission policy.", "Beethoven");
    return;
  }
  if (event.type === "validation_completed") {
    updateLiveTask(event.task_id, {
      status: event.blocked?.length ? "blocked" : "completed",
      reason: event.blocked?.length ? "validation blocked by policy" : "validation completed"
    });
    return;
  }
  if (event.type === "score_completed") {
    composerStatus.textContent = "Score completed. Saving session…";
    updateAssistantDraft("Score completed. Preparing the final response…", "Beethoven");
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
      body: JSON.stringify(scoreRequestPayload(objective))
    });
    if (!response.ok) {
      return;
    }
    const score = await response.json();
    scoreTasks = score.tasks.map((task) => taskFromScore(task));
    scoreId.textContent = score.id;
    currentScore = score;
    currentRunContext = null;
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
      body: JSON.stringify(scoreRequestPayload(objective))
    });
    if (!response.ok) {
      throw new Error(`Score API returned ${response.status}`);
    }
    const score = await response.json();
    scoreTasks = score.tasks.map((task) => taskFromScore(task));
    scoreId.textContent = score.id;
    currentScore = score;
    currentRunContext = null;
    preferReaderForAttachedScore(score);
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

async function loadValidationProfiles() {
  try {
    const response = await fetch("/api/validation-profiles");
    if (!response.ok) {
      throw new Error(`Validation profiles API returned ${response.status}`);
    }
    const payload = await response.json();
    renderValidationProfiles(payload.profiles ?? []);
  } catch {
    renderValidationProfiles([
      {
        id: "desktop",
        name: "Desktop JS",
        description: "Check the desktop application JavaScript syntax.",
        commands: ["node --check desktop/app.js"]
      },
      {
        id: "full",
        name: "Full local gate",
        description: "Run the local validation gate.",
        commands: ["node --check desktop/app.js", ".venv/bin/ruff check .", ".venv/bin/python -m pytest"]
      }
    ]);
  }
}

async function loadRuntimeStatus() {
  refreshRuntimeButton.textContent = "Refreshing…";
  refreshRuntimeButton.disabled = true;
  try {
    const [orchestratorResponse, soloMlxResponse, packagingResponse] = await Promise.all([
      fetch("/api/orchestrator"),
      fetch("/api/solomlx"),
      fetch("/api/packaging")
    ]);
    if (!orchestratorResponse.ok || !soloMlxResponse.ok || !packagingResponse.ok) {
      throw new Error("Runtime status API returned an error.");
    }
    const orchestratorPayload = await orchestratorResponse.json();
    const soloMlxPayload = await soloMlxResponse.json();
    const packagingPayload = await packagingResponse.json();
    runtimeStatus = {
      ...runtimeStatus,
      orchestrator: orchestratorPayload.orchestrator ?? null,
      solomlx: soloMlxPayload.solomlx ?? null,
      packaging: packagingPayload.packaging ?? null
    };
  } catch (error) {
    runtimeStatus = {
      ...runtimeStatus,
      orchestrator: {
        status: "unavailable",
        available: false,
        message: "Unable to reach Beethoven's runtime status endpoints."
      },
      solomlx: {
        status: "unavailable",
        available: false,
        message: "Unable to reach SoloMLX status endpoint."
      },
      packaging: {
        status: "unavailable",
        ready: false,
        message: "Unable to reach packaging diagnostic endpoint."
      }
    };
    console.error(error);
  } finally {
    renderRuntimeStatus();
    refreshRuntimeButton.textContent = "Refresh runtime";
    refreshRuntimeButton.disabled = false;
  }
}

async function runSoloMlxAction(button, label, endpoint, method = "POST", body = {}) {
  button.textContent = `${label}…`;
  button.disabled = true;
  try {
    const response = await fetch(endpoint, {
      method,
      headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
      body: method === "POST" ? JSON.stringify(body) : undefined
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error ?? `SoloMLX API returned ${response.status}`);
    }
    runtimeStatus = {
      ...runtimeStatus,
      solomlx: payload.solomlx ?? runtimeStatus.solomlx
    };
    renderRuntimeStatus();
    await loadRuntimeStatus();
    await loadSoloists();
  } catch (error) {
    runtimeStatus = {
      ...runtimeStatus,
      solomlx: {
        status: "action_failed",
        available: false,
        message: error.message ?? "SoloMLX action failed."
      }
    };
    renderRuntimeStatus();
    console.error(error);
  } finally {
    button.textContent = label;
    button.disabled = false;
  }
}

async function loadRecursiveMasConfig() {
  try {
    const response = await fetch("/api/soloists/recursivemas/config");
    if (!response.ok) {
      throw new Error(`RecursiveMAS config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderRecursiveMasConfig(payload.config ?? {});
  } catch (error) {
    console.error(error);
  }
}

async function loadOpenAiConfig() {
  try {
    const response = await fetch("/api/soloists/openai-compatible/config");
    if (!response.ok) {
      throw new Error(`OpenAI-compatible config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderOpenAiConfig(payload.config ?? {});
  } catch (error) {
    console.error(error);
  }
}

async function saveRecursiveMasConfig() {
  const command = recursiveMasCommand.value.trim();
  if (!command) {
    recursiveMasCommand.focus();
    return;
  }
  saveRecursiveMasButton.textContent = "Saving…";
  saveRecursiveMasButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/recursivemas/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command })
    });
    if (!response.ok) {
      throw new Error(`RecursiveMAS config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderRecursiveMasConfig(payload.config ?? {});
    await checkRecursiveMas();
    await loadSoloists();
  } catch (error) {
    renderSoloistCheck({
      id: "recursivemas",
      status: "config_failed",
      available: false,
      message: "Unable to save RecursiveMAS command."
    });
    console.error(error);
  } finally {
    saveRecursiveMasButton.textContent = "Save";
    saveRecursiveMasButton.disabled = false;
  }
}

async function clearRecursiveMasConfig() {
  clearRecursiveMasButton.textContent = "Clearing…";
  clearRecursiveMasButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/recursivemas/config", {
      method: "DELETE"
    });
    if (!response.ok) {
      throw new Error(`RecursiveMAS config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderRecursiveMasConfig(payload.config ?? {});
    await checkRecursiveMas();
    await loadSoloists();
  } catch (error) {
    renderSoloistCheck({
      id: "recursivemas",
      status: "clear_failed",
      available: false,
      message: "Unable to clear RecursiveMAS command."
    });
    console.error(error);
  } finally {
    clearRecursiveMasButton.textContent = "Clear";
    clearRecursiveMasButton.disabled = false;
  }
}

async function checkOpenAiCompatible() {
  checkOpenAiButton.textContent = "Checking…";
  checkOpenAiButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/openai-compatible/check");
    const payload = await response.json();
    renderSoloistCheck(payload.check ?? {});
  } catch (error) {
    renderSoloistCheck({
      id: "openai-compatible",
      status: "unavailable",
      available: false,
      message: "Unable to reach the OpenAI-compatible check endpoint."
    });
    console.error(error);
  } finally {
    checkOpenAiButton.textContent = "Check OpenAI API";
    checkOpenAiButton.disabled = false;
  }
}

async function saveOpenAiConfig() {
  const baseUrl = openAiBaseUrl.value.trim();
  if (!baseUrl) {
    openAiBaseUrl.focus();
    return;
  }
  saveOpenAiButton.textContent = "Saving…";
  saveOpenAiButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/openai-compatible/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_url: baseUrl,
        model: openAiModel.value.trim(),
        api_key: openAiApiKey.value.trim()
      })
    });
    if (!response.ok) {
      throw new Error(`OpenAI-compatible config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderOpenAiConfig(payload.config ?? {});
    await checkOpenAiCompatible();
    await loadSoloists();
    await loadSkills();
  } catch (error) {
    renderSoloistCheck({
      id: "openai-compatible",
      status: "config_failed",
      available: false,
      message: "Unable to save OpenAI-compatible config."
    });
    console.error(error);
  } finally {
    saveOpenAiButton.textContent = "Save API";
    saveOpenAiButton.disabled = false;
  }
}

async function clearOpenAiConfig() {
  clearOpenAiButton.textContent = "Clearing…";
  clearOpenAiButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/openai-compatible/config", {
      method: "DELETE"
    });
    if (!response.ok) {
      throw new Error(`OpenAI-compatible config API returned ${response.status}`);
    }
    const payload = await response.json();
    renderOpenAiConfig(payload.config ?? {});
    await checkOpenAiCompatible();
    await loadSoloists();
    await loadSkills();
  } catch (error) {
    renderSoloistCheck({
      id: "openai-compatible",
      status: "clear_failed",
      available: false,
      message: "Unable to clear OpenAI-compatible config."
    });
    console.error(error);
  } finally {
    clearOpenAiButton.textContent = "Clear API";
    clearOpenAiButton.disabled = false;
  }
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

async function inspectWorkspaceDiff() {
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Loading workspace diff…";
  try {
    const response = await fetch("/api/diff");
    if (!response.ok) {
      throw new Error(`Diff API returned ${response.status}`);
    }
    const payload = await response.json();
    const diff = payload.diff ?? {};
    const body = diff.diff
      ? `${diff.message}${diff.truncated ? " Diff truncated." : ""}\n\n${diff.diff}`
      : diff.message ?? "No workspace diff.";
    chatMessages.push({
      role: "assistant",
      meta: "Workspace diff",
      content: body,
    });
    renderChat();
    composerStatus.textContent = diff.status === "dirty" ? "Workspace diff loaded." : "Workspace has no diff.";
    sessionPanel.hidden = true;
    moreOptionsButton.classList.remove("active");
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent = "Unable to load workspace diff.";
    console.error(error);
  }
}

function renderPatchResult(report) {
  patchResult.hidden = false;
  patchResult.classList.toggle("available", Boolean(report.applicable || report.applied));
  patchResult.classList.toggle("unavailable", !Boolean(report.applicable || report.applied));
  patchApprovalToken.value = report.token ?? patchApprovalToken.value;
  const summary = report.summary ?? {};
  const files = Array.isArray(summary.files) ? summary.files : [];
  const output = [
    report.stdout ? { label: "stdout", value: report.stdout } : null,
    report.stderr ? { label: "stderr", value: report.stderr } : null,
  ].filter(Boolean);
  patchResult.innerHTML = `
    <strong>${escapeHtml(report.status ?? "patch")} · ${escapeHtml(report.applied ? "applied" : report.applicable ? "applicable" : "blocked")}</strong>
    <p>${escapeHtml(report.message ?? "No patch report returned.")}</p>
    ${renderPatchSummary(summary)}
    ${files.length ? renderPatchFiles(files) : ""}
    ${report.token ? `<p>Approval token <code>${escapeHtml(report.token)}</code></p>` : ""}
    ${output.map((item) => renderPatchOutput(item.label, item.value)).join("")}
  `;
}

function renderPatchSummary(summary) {
  if (!summary || typeof summary !== "object" || summary.file_count === undefined) {
    return "";
  }
  return `
    <div class="patch-summary-grid">
      <div><span>Files</span><strong>${escapeHtml(String(summary.file_count ?? 0))}</strong></div>
      <div><span>Additions</span><strong>+${escapeHtml(String(summary.additions ?? 0))}</strong></div>
      <div><span>Deletions</span><strong>-${escapeHtml(String(summary.deletions ?? 0))}</strong></div>
    </div>
    ${summary.truncated ? '<p>Patch file list truncated by safety limits.</p>' : ""}
  `;
}

function renderPatchFiles(files) {
  return `
    <div class="patch-file-list">
      ${files.map((file) => `
        <div class="patch-file-row">
          <div>
            <strong>${escapeHtml(file.path ?? "unknown")}</strong>
            <span>${escapeHtml(file.change_type ?? "modified")}</span>
          </div>
          <span class="patch-line-count">+${escapeHtml(String(file.additions ?? 0))} / -${escapeHtml(String(file.deletions ?? 0))}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderPatchOutput(label, value) {
  const cleanValue = String(value ?? "").trim();
  if (!cleanValue) {
    return "";
  }
  return `
    <details class="patch-output">
      <summary>${escapeHtml(label)}</summary>
      <pre>${escapeHtml(cleanValue)}</pre>
    </details>
  `;
}

async function checkPatch() {
  const patch = patchInput.value.trim();
  if (!patch) {
    patchInput.focus();
    return;
  }
  checkPatchButton.textContent = "Checking…";
  checkPatchButton.disabled = true;
  try {
    const response = await fetch("/api/patch/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patch })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error ?? payload.patch?.message ?? `Patch API returned ${response.status}`);
    }
    renderPatchResult(payload.patch ?? {});
  } catch (error) {
    renderPatchResult({ status: "error", applicable: false, message: error.message ?? "Patch check failed." });
    console.error(error);
  } finally {
    checkPatchButton.textContent = "Check patch";
    checkPatchButton.disabled = false;
  }
}

async function applyCheckedPatch() {
  const patch = patchInput.value.trim();
  const approvalToken = patchApprovalToken.value.trim();
  if (!patch || !approvalToken) {
    patchInput.focus();
    return;
  }
  applyPatchButton.textContent = "Applying…";
  applyPatchButton.disabled = true;
  try {
    const response = await fetch("/api/patch/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patch, approval_token: approvalToken })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error ?? payload.patch?.message ?? `Patch API returned ${response.status}`);
    }
    renderPatchResult(payload.patch ?? {});
    await loadWorkspace();
  } catch (error) {
    renderPatchResult({ status: "error", applied: false, message: error.message ?? "Patch apply failed." });
    console.error(error);
  } finally {
    applyPatchButton.textContent = "Apply patch";
    applyPatchButton.disabled = false;
  }
}

function togglePatchPanel(open = patchPanel.hidden) {
  patchPanel.hidden = !open;
  sessionPanel.hidden = true;
  moreOptionsButton.classList.toggle("active", open);
  if (open) {
    patchInput.focus();
  }
}

function renderValidationApprovalPanel() {
  const commands = pendingValidationApproval?.commands ?? [];
  validationPanelMeta.textContent = pendingValidationApproval?.objective
    ? `Blocked validation for: ${pendingValidationApproval.objective}`
    : "Review blocked commands before rerunning.";
  validationCommandList.innerHTML = commands.length
    ? commands.map((item) => `
        <article class="validation-command-card">
          <code>${escapeHtml(item.command)}</code>
          <p>Risk: ${escapeHtml(item.risk ?? "unknown")}</p>
          <p>${escapeHtml(item.reason ?? "Blocked by validation policy.")}</p>
        </article>
      `).join("")
    : '<div class="session-empty">No blocked validation commands.</div>';
  approveValidationButton.disabled = !commands.length;
}

function toggleValidationPanel(open = validationPanel.hidden) {
  validationPanel.hidden = !open;
  if (open) {
    hideUtilityPanels();
    validationPanel.hidden = false;
    renderValidationApprovalPanel();
  }
}

async function checkRecursiveMas() {
  checkRecursiveMasButton.textContent = "Checking…";
  checkRecursiveMasButton.disabled = true;
  try {
    const response = await fetch("/api/soloists/recursivemas/check");
    const payload = await response.json();
    const report = payload.check ?? {};
    runtimeStatus = {
      ...runtimeStatus,
      recursivemas: report
    };
    renderRuntimeStatus();
    renderSoloistCheck(report);
  } catch (error) {
    const report = {
      id: "recursivemas",
      status: "unavailable",
      available: false,
      message: "Unable to reach the desktop RecursiveMAS check endpoint."
    };
    runtimeStatus = {
      ...runtimeStatus,
      recursivemas: report
    };
    renderRuntimeStatus();
    renderSoloistCheck(report);
    console.error(error);
  } finally {
    checkRecursiveMasButton.textContent = "Check RecursiveMAS";
    checkRecursiveMasButton.disabled = false;
  }
}

async function loadSessions() {
  allSessions = await fetchSessions();
  renderFilteredSessions();
}

async function clearSessionHistory() {
  if (!allSessions.length) {
    composerStatus.classList.remove("error");
    composerStatus.textContent = "No sessions to clear.";
    return;
  }
  if (!window.confirm("Clear local session history?")) {
    return;
  }
  clearSessionsButton.disabled = true;
  composerStatus.classList.remove("error");
  composerStatus.textContent = "Clearing sessions…";
  try {
    const response = await fetch("/api/sessions", { method: "DELETE" });
    if (!response.ok) {
      throw new Error(`Session API returned ${response.status}`);
    }
    allSessions = [];
    activeSessionId = null;
    renderFilteredSessions();
    composerStatus.textContent = "Session history cleared.";
  } catch (error) {
    composerStatus.classList.add("error");
    composerStatus.textContent = "Unable to clear session history.";
    console.error(error);
  } finally {
    clearSessionsButton.disabled = false;
  }
}

async function startNewTask() {
  activeSessionId = null;
  composer.value = "";
  sessionSearch.value = "";
  scoreTasks = [];
  currentScore = null;
  currentRunContext = null;
  chatMessages = [];
  pendingValidationApproval = null;
  pageTitle.textContent = "New task";
  setSearchOpen(false);
  composerStatus.classList.remove("error");
  composerStatus.textContent = "New task ready.";
  permissionSelect.value = "ask";
  effortSelect.value = "medium";
  soloistSelect.value = "auto";
  validationCommandInput.value = "";
  commandPanel.hidden = true;
  skillsPanel.hidden = true;
  scorePanel.hidden = true;
  filesPanel.hidden = true;
  sessionPanel.hidden = true;
  patchPanel.hidden = true;
  validationPanel.hidden = true;
  patchInput.value = "";
  patchApprovalToken.value = "";
  patchResult.hidden = true;
  scorePreviewButton.classList.remove("active");
  attachFilesButton.classList.remove("active");
  moreOptionsButton.classList.remove("active");
  document.querySelectorAll(".nav-action").forEach((button) => {
    button.classList.toggle("active", button === newTaskButton);
  });
  renderChat();
  renderScore();
  renderFilteredSessions();
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
clearSessionsButton.addEventListener("click", clearSessionHistory);
sessionSearch.addEventListener("input", renderFilteredSessions);
sessionSearch.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    sessionSearch.value = "";
    renderFilteredSessions();
    setSearchOpen(false);
  }
});
terminalButton.addEventListener("click", () => toggleCommandPanel());
moreOptionsButton.addEventListener("click", () => toggleSessionPanel());
attachFilesButton.addEventListener("click", () => toggleFilesPanel());
slashCommandsButton.addEventListener("click", () => toggleCommandPanel(true));
scorePreviewButton.addEventListener("click", previewComposerScore);
chatThread.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (target.dataset.chatAction === "approve-validation") {
    approveBlockedValidation();
  }
  if (target.dataset.chatAction === "review-validation") {
    toggleValidationPanel(true);
  }
});
closeCommandPanel.addEventListener("click", () => toggleCommandPanel(false));
closeSkillsPanel.addEventListener("click", () => toggleSkillsPanel(false));
refreshRuntimeButton.addEventListener("click", loadRuntimeStatus);
ensureSoloMlxButton.addEventListener("click", () =>
  runSoloMlxAction(ensureSoloMlxButton, "Ensure SoloMLX", "/api/solomlx/ensure", "POST", {
    start: true,
    prepare: false,
    install: false
  })
);
installSoloMlxButton.addEventListener("click", () =>
  runSoloMlxAction(installSoloMlxButton, "Install SoloMLX", "/api/solomlx/install")
);
prepareSoloMlxButton.addEventListener("click", () =>
  runSoloMlxAction(prepareSoloMlxButton, "Prepare Ministral", "/api/solomlx/prepare-orchestrator")
);
startSoloMlxButton.addEventListener("click", () =>
  runSoloMlxAction(startSoloMlxButton, "Start SoloMLX", "/api/solomlx/start")
);
stopSoloMlxButton.addEventListener("click", () =>
  runSoloMlxAction(stopSoloMlxButton, "Stop SoloMLX", "/api/solomlx", "DELETE")
);
checkRecursiveMasButton.addEventListener("click", checkRecursiveMas);
saveRecursiveMasButton.addEventListener("click", saveRecursiveMasConfig);
clearRecursiveMasButton.addEventListener("click", clearRecursiveMasConfig);
checkOpenAiButton.addEventListener("click", checkOpenAiCompatible);
saveOpenAiButton.addEventListener("click", saveOpenAiConfig);
clearOpenAiButton.addEventListener("click", clearOpenAiConfig);
closeScorePanel.addEventListener("click", () => toggleScorePanel(false));
closeFilesPanel.addEventListener("click", () => toggleFilesPanel(false));
closeSessionPanel.addEventListener("click", () => toggleSessionPanel(false));
closePatchPanel.addEventListener("click", () => togglePatchPanel(false));
closeValidationPanel.addEventListener("click", () => toggleValidationPanel(false));
cancelValidationApprovalButton.addEventListener("click", () => toggleValidationPanel(false));
approveValidationButton.addEventListener("click", approveBlockedValidation);
copyScoreIdButton.addEventListener("click", async () => {
  await copyText(scoreId.textContent, "score ID");
  toggleSessionPanel(false);
});
insertSessionCommandButton.addEventListener("click", () => {
  const command = activeSessionId
    ? `beethoven sessions show ${activeSessionId}`
    : `beethoven score "${currentScore?.objective ?? "new orchestration task"}"`;
  insertCommand(command);
  toggleSessionPanel(false);
});
exportScoreButton.addEventListener("click", () => {
  exportCurrentScore();
  toggleSessionPanel(false);
});
inspectDiffButton.addEventListener("click", inspectWorkspaceDiff);
openCommandsFromMenuButton.addEventListener("click", () => toggleCommandPanel(true));
openPatchPanelButton.addEventListener("click", () => togglePatchPanel(true));
checkPatchButton.addEventListener("click", checkPatch);
applyPatchButton.addEventListener("click", applyCheckedPatch);
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
soloistSelect.addEventListener("change", () => updateInspectorState(currentRunContext));
renderCommandList();
setConversationForMode("code");
renderScore();
loadBackendHealth();
loadWorkspace();
loadSoloists();
loadSkills();
loadValidationProfiles();
loadRuntimeStatus();
checkRecursiveMas();
loadRecursiveMasConfig();
loadOpenAiConfig();
loadFiles();
loadSessions();
