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

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderScore() {
  scoreList.innerHTML = scoreTasks
    .map(
      (task) => `
        <article class="score-card">
          <header>
            <h3>${task.id}</h3>
            <span class="pill success">completed</span>
          </header>
          <p>${task.instruction}</p>
          <div class="route-reason">${task.capability} → ${task.soloist}: ${task.reason}</div>
        </article>
      `
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
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective: "desktop and CLI foundation" })
    });
    if (!response.ok) {
      return;
    }
    const context = await response.json();
    scoreTasks = context.score.tasks.map((task) => taskFromApi(task, context));
    scoreId.textContent = context.score.id;
  } catch {
    composerStatus.textContent = "Static preview mode. Start `beethoven desktop` for live runs.";
  } finally {
    renderScore();
  }
}

composer.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    runComposer();
  }
});

sendButton.addEventListener("click", runComposer);
renderScore();
loadInitialScore();
