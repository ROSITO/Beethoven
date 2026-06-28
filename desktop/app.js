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
const modeTabs = [...document.querySelectorAll(".mode-tab")];
const modeEyebrow = document.querySelector("#modeEyebrow");
const modeSummary = document.querySelector("#modeSummary");
const modeConductor = document.querySelector("#modeConductor");

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

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
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
    sessionList.innerHTML = '<div class="session-empty">No runs yet</div>';
    return;
  }

  sessionList.innerHTML = sessions
    .map((session, index) => {
      const recency = index === 0 ? "now" : session.branch ?? "main";
      const activeClass = index === 0 ? " active" : "";
      const runningClass = index === 0 ? " running" : "";
      return `
        <button class="session-row${activeClass}" type="button" data-session-id="${session.id}">
          <span class="status-dot${runningClass}"></span>
          ${session.title}
          <span class="row-meta">${recency}</span>
        </button>
      `;
    })
    .join("");
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
      body: JSON.stringify({ objective: value })
    });
    if (!response.ok) {
      throw new Error(`Desktop API returned ${response.status}`);
    }
    const context = await response.json();
    scoreTasks = context.score.tasks.map((task) => taskFromApi(task, context));
    scoreId.textContent = context.score.id;
    renderScore();
    const sessions = await fetchSessions();
    renderSessions([context.session, ...sessions.filter((item) => item.id !== context.session.id)]);
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

async function loadInitialScore() {
  try {
    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective: "desktop and CLI foundation" })
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

async function loadSessions() {
  const sessions = await fetchSessions();
  renderSessions(sessions);
}

composer.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    runComposer();
  }
});

sendButton.addEventListener("click", runComposer);
modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});
renderScore();
loadSessions();
loadInitialScore();
