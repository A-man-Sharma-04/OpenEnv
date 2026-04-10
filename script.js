const DEFAULT_API_BASE_URL = "http://localhost:7860";

const elements = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  taskId: document.getElementById("taskId"),
  actionInput: document.getElementById("actionInput"),
  resetBtn: document.getElementById("resetBtn"),
  stateBtn: document.getElementById("stateBtn"),
  stepBtn: document.getElementById("stepBtn"),
  clearLogsBtn: document.getElementById("clearLogsBtn"),
  status: document.getElementById("status"),
  stateOutput: document.getElementById("stateOutput"),
  rewardValue: document.getElementById("rewardValue"),
  doneValue: document.getElementById("doneValue"),
  logsList: document.getElementById("logsList")
};

const appState = {
  logs: [],
  loading: false
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

function renderJson(value) {
  elements.stateOutput.textContent = JSON.stringify(value ?? {}, null, 2);
}

function updateRewardAndDone(reward, done) {
  const normalizedReward =
    reward && typeof reward === "object" && "value" in reward
      ? reward.value
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
  const taskId = elements.taskId.value.trim() || "easy";
  const template = {
    task_id: taskId,
    action_type: "analysis",
    payload: "Describe your reasoning here",
    confidence: 0.75
  };
  elements.actionInput.value = JSON.stringify(template, null, 2);
}

function initialize() {
  const savedApiBaseUrl = localStorage.getItem("openenv.apiBaseUrl");
  elements.apiBaseUrl.value = savedApiBaseUrl || DEFAULT_API_BASE_URL;

  setDefaultActionTemplate();
  renderJson({});
  updateRewardAndDone(undefined, undefined);
  renderLogs();

  elements.apiBaseUrl.addEventListener("change", () => {
    persistApiBaseUrl();
    checkBackendConnection();
  });

  elements.taskId.addEventListener("change", setDefaultActionTemplate);
  elements.resetBtn.addEventListener("click", resetEnvironment);
  elements.stepBtn.addEventListener("click", stepEnvironment);
  elements.stateBtn.addEventListener("click", fetchState);
  elements.clearLogsBtn.addEventListener("click", clearLogs);

  checkBackendConnection().then((isConnected) => {
    if (isConnected) {
      fetchState();
    }
  });
}

initialize();
