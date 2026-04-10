const DEFAULT_API_BASE_URL = "http://localhost:7860";

const elements = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  taskId: document.getElementById("taskId"),
  presetSelect: document.getElementById("presetSelect"),
  applyPresetBtn: document.getElementById("applyPresetBtn"),
  actionInput: document.getElementById("actionInput"),
  resetBtn: document.getElementById("resetBtn"),
  stateBtn: document.getElementById("stateBtn"),
  stepBtn: document.getElementById("stepBtn"),
  copyCurlBtn: document.getElementById("copyCurlBtn"),
  clearLogsBtn: document.getElementById("clearLogsBtn"),
  status: document.getElementById("status"),
  stateOutput: document.getElementById("stateOutput"),
  rewardValue: document.getElementById("rewardValue"),
  doneValue: document.getElementById("doneValue"),
  logsList: document.getElementById("logsList"),
  statSteps: document.getElementById("statSteps"),
  statReward: document.getElementById("statReward"),
  statSuccess: document.getElementById("statSuccess"),
  statLastStep: document.getElementById("statLastStep")
};

const appState = {
  logs: [],
  loading: false,
  stats: {
    stepsSent: 0,
    totalReward: 0,
    doneTrue: 0,
    lastStepAt: null
  }
};

const PRESET_BUILDERS = {
  analysis(taskId) {
    return {
      task_id: taskId,
      action_type: "analysis",
      payload: "Describe your reasoning here",
      confidence: 0.75
    };
  },
  explore(taskId) {
    return {
      task_id: taskId,
      action_type: "explore",
      payload: {
        strategy: "sample-diverse-paths",
        budget: 3,
        note: "Collect alternatives before committing."
      },
      confidence: 0.68
    };
  },
  verify(taskId) {
    return {
      task_id: taskId,
      action_type: "verify",
      payload: {
        checks: ["constraints", "format", "scoring"],
        strict: true
      },
      confidence: 0.84
    };
  },
  hard_mode() {
    return {
      task_id: "hard",
      action_type: "policy",
      payload: {
        objective: "maximize_consistency",
        fallback: "safe_rollback",
        depth: 4
      },
      confidence: 0.72
    };
  }
};

function getApiBaseUrl() {
  const raw = elements.apiBaseUrl.value.trim();
  return (raw || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function persistApiBaseUrl() {
  localStorage.setItem("openenv.apiBaseUrl", getApiBaseUrl());
}

function setLoading(isLoading) {
  appState.loading = isLoading;
  elements.resetBtn.disabled = isLoading;
  elements.stateBtn.disabled = isLoading;
  elements.stepBtn.disabled = isLoading;
}

function setStatus(message, type = "") {
  elements.status.textContent = message;
  elements.status.className = `status ${type}`.trim();
}

function renderStats() {
  const { stepsSent, totalReward, doneTrue, lastStepAt } = appState.stats;
  const successRate = stepsSent > 0 ? (doneTrue / stepsSent) * 100 : 0;

  elements.statSteps.textContent = String(stepsSent);
  elements.statReward.textContent = Number(totalReward).toFixed(2);
  elements.statSuccess.textContent = `${Math.round(successRate)}%`;
  elements.statLastStep.textContent = lastStepAt || "-";
}

function resetStats() {
  appState.stats.stepsSent = 0;
  appState.stats.totalReward = 0;
  appState.stats.doneTrue = 0;
  appState.stats.lastStepAt = null;
  renderStats();
}

function updateStatsFromStep(reward, done) {
  appState.stats.stepsSent += 1;

  const normalizedReward =
    reward && typeof reward === "object" && "score" in reward ? reward.score : reward;
  const rewardNumber = Number(normalizedReward);
  if (Number.isFinite(rewardNumber)) {
    appState.stats.totalReward += rewardNumber;
  }

  if (done === true) {
    appState.stats.doneTrue += 1;
  }

  appState.stats.lastStepAt = new Date().toLocaleTimeString();
  renderStats();
}

function renderJson(value) {
  elements.stateOutput.textContent = JSON.stringify(value ?? {}, null, 2);
}

function updateRewardAndDone(reward, done) {
  const normalizedReward =
    reward && typeof reward === "object" && "score" in reward
      ? reward.score
      : reward;

  const hasReward = normalizedReward !== undefined && normalizedReward !== null;
  elements.rewardValue.textContent = hasReward ? String(normalizedReward) : "-";

  if (done === true) {
    elements.doneValue.textContent = "true";
    elements.doneValue.style.color = "#1f7a68";
  } else if (done === false) {
    elements.doneValue.textContent = "false";
    elements.doneValue.style.color = "#b44b2e";
  } else {
    elements.doneValue.textContent = "-";
    elements.doneValue.style.color = "";
  }
}

function addLog({ action, reward }) {
  appState.logs.unshift({
    action,
    reward,
    timestamp: new Date().toLocaleTimeString()
  });
  renderLogs();
}

function clearLogs() {
  appState.logs = [];
  renderLogs();
}

function renderLogs() {
  if (!appState.logs.length) {
    elements.logsList.innerHTML = "<li>No logs yet.</li>";
    return;
  }

  elements.logsList.innerHTML = appState.logs
    .map((log) => {
      const actionText = typeof log.action === "string"
        ? log.action
        : JSON.stringify(log.action, null, 2);

      const rewardText = log.reward !== undefined && log.reward !== null
        ? String(log.reward)
        : "-";

      return `
        <li>
          <div class="log-meta">${log.timestamp}</div>
          <div><strong>Reward:</strong> ${rewardText}</div>
          <div class="log-action"><strong>Action:</strong> ${escapeHtml(actionText)}</div>
        </li>
      `;
    })
    .join("");
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function getSelectedPresetAction() {
  const taskId = elements.taskId.value.trim() || "easy";
  const presetKey = elements.presetSelect.value;
  const builder = PRESET_BUILDERS[presetKey] || PRESET_BUILDERS.analysis;
  return builder(taskId);
}

function applyPresetToEditor() {
  const action = getSelectedPresetAction();
  elements.actionInput.value = JSON.stringify(action, null, 2);
  setStatus("Preset applied to Action JSON.", "ok");
}

async function copyCurlCommand() {
  const payload = elements.actionInput.value.trim();
  if (!payload) {
    setStatus("Action JSON is empty. Nothing to copy.", "error");
    return;
  }

  const baseUrl = getApiBaseUrl();
  const escapedPayload = payload.replaceAll("'", "''");
  const curlCommand = `curl -X POST ${baseUrl}/step -H \"Content-Type: application/json\" -d '${escapedPayload}'`;

  try {
    await navigator.clipboard.writeText(curlCommand);
    setStatus("cURL command copied to clipboard.", "ok");
  } catch {
    setStatus("Clipboard blocked. Copy action manually from the editor.", "error");
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`;
    let detail = fallback;

    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") {
        detail = payload.detail;
      } else {
        detail = JSON.stringify(payload);
      }
    } catch {
      detail = fallback;
    }

    throw new Error(detail);
  }

  return response.json();
}

async function checkBackendConnection() {
  setStatus("Checking backend connection...");

  try {
    await request("/health", { method: "GET" });
    setStatus(`Connected to backend at ${getApiBaseUrl()}.`, "ok");
    return true;
  } catch (error) {
    setStatus(`Backend unreachable: ${error.message}`, "error");
    return false;
  }
}

async function resetEnvironment() {
  const taskId = elements.taskId.value.trim() || "easy";

  setLoading(true);
  setStatus("Resetting environment...");

  try {
    const data = await request("/reset", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId })
    });

    renderJson(data);
    updateRewardAndDone(undefined, undefined);
    clearLogs();
    resetStats();
    setStatus("Environment reset successfully.", "ok");
  } catch (error) {
    setStatus(`Reset failed: ${error.message}`, "error");
  } finally {
    setLoading(false);
  }
}

async function stepEnvironment() {
  const raw = elements.actionInput.value.trim();
  if (!raw) {
    setStatus("Action JSON is empty.", "error");
    return;
  }

  let action;
  try {
    action = JSON.parse(raw);
  } catch (error) {
    setStatus(`Invalid JSON: ${error.message}`, "error");
    return;
  }

  setLoading(true);
  setStatus("Sending action...");

  try {
    const data = await request("/step", {
      method: "POST",
      body: JSON.stringify(action)
    });

    const observation = data.observation ?? data.state ?? data;
    renderJson(observation);
    updateRewardAndDone(data.reward, data.done);
    addLog({ action, reward: data.reward });
    updateStatsFromStep(data.reward, data.done);
    setStatus("Action executed successfully.", "ok");
  } catch (error) {
    setStatus(`Step failed: ${error.message}`, "error");
  } finally {
    setLoading(false);
  }
}

async function fetchState() {
  setLoading(true);
  setStatus("Fetching current state...");

  try {
    const data = await request("/state", { method: "GET" });
    renderJson(data);
    setStatus("State loaded.", "ok");
  } catch (error) {
    setStatus(`State fetch failed: ${error.message}`, "error");
  } finally {
    setLoading(false);
  }
}

function setDefaultActionTemplate() {
  applyPresetToEditor();
}

function initialize() {
  const savedApiBaseUrl = localStorage.getItem("openenv.apiBaseUrl");
  elements.apiBaseUrl.value = savedApiBaseUrl || DEFAULT_API_BASE_URL;

  setDefaultActionTemplate();
  renderJson({});
  updateRewardAndDone(undefined, undefined);
  renderLogs();
  renderStats();

  elements.apiBaseUrl.addEventListener("change", () => {
    persistApiBaseUrl();
    checkBackendConnection();
  });

  elements.taskId.addEventListener("change", setDefaultActionTemplate);
  elements.presetSelect.addEventListener("change", applyPresetToEditor);
  elements.applyPresetBtn.addEventListener("click", applyPresetToEditor);
  elements.resetBtn.addEventListener("click", resetEnvironment);
  elements.stepBtn.addEventListener("click", stepEnvironment);
  elements.stateBtn.addEventListener("click", fetchState);
  elements.clearLogsBtn.addEventListener("click", clearLogs);
  elements.copyCurlBtn.addEventListener("click", copyCurlCommand);

  checkBackendConnection().then((isConnected) => {
    if (isConnected) {
      fetchState();
    }
  });
}

initialize();
