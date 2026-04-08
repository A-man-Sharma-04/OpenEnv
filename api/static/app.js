const root = window.location.origin;
const appState = {
  busy: false,
};

function toJson(value) {
  try {
    return JSON.parse(value);
  } catch (error) {
    return null;
  }
}

function showResponse(id, data) {
  document.getElementById(id).textContent = JSON.stringify(data, null, 2);
}

function setGlobalStatus(message, kind = 'info') {
  const status = document.getElementById('global-status');
  if (!status) {
    return;
  }
  status.textContent = message;
  status.dataset.kind = kind;
}

function setBusy(isBusy) {
  appState.busy = isBusy;
  document.querySelectorAll('button').forEach((button) => {
    button.disabled = isBusy;
    button.classList.toggle('is-loading', isBusy);
  });
}

async function postJson(path, body) {
  const response = await fetch(`${root}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function getJson(path) {
  const response = await fetch(`${root}${path}`);
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function getValue(id) {
  return document.getElementById(id).value;
}

async function createTask() {
  const envType = getValue('task-env');
  const config = toJson(getValue('task-config'));
  if (!config) {
    showResponse('task-response', { error: 'Invalid JSON in task config' });
    return;
  }

  const body = { env_type: envType, config };
  try {
    setBusy(true);
    setGlobalStatus('Creating task...', 'info');
    const result = await postJson('/task/create', body);
    showResponse('task-response', result);
    setGlobalStatus('Task created successfully.', 'success');
  } catch (error) {
    showResponse('task-response', { error: error.message });
    setGlobalStatus('Task creation failed.', 'error');
  } finally {
    setBusy(false);
  }
}

async function startEvaluation() {
  const taskConfig = toJson(getValue('eval-task-config'));
  const agentConfig = toJson(getValue('agent-config'));
  if (!taskConfig || !agentConfig) {
    showResponse('eval-response', { error: 'Invalid JSON in task or agent config' });
    return;
  }

  const body = {
    task: {
      env_type: getValue('eval-env'),
      config: taskConfig,
    },
    agent: {
      agent_type: getValue('agent-type'),
      config: agentConfig,
    },
    num_episodes: Number(getValue('num-episodes')) || 10,
    max_steps: Number(getValue('max-steps')) || 100,
  };

  try {
    setBusy(true);
    setGlobalStatus('Starting evaluation...', 'info');
    const result = await postJson('/evaluate', body);
    showResponse('eval-response', result);
    setGlobalStatus('Evaluation started.', 'success');
  } catch (error) {
    showResponse('eval-response', { error: error.message });
    setGlobalStatus('Evaluation request failed.', 'error');
  } finally {
    setBusy(false);
  }
}

async function checkStatus() {
  const evaluationId = getValue('status-id').trim();
  if (!evaluationId) {
    showResponse('status-response', { error: 'Evaluation ID is required' });
    return;
  }

  try {
    setBusy(true);
    setGlobalStatus('Checking evaluation status...', 'info');
    const result = await getJson(`/evaluate/${evaluationId}`);
    showResponse('status-response', result);
    setGlobalStatus('Evaluation status updated.', 'success');
  } catch (error) {
    showResponse('status-response', { error: error.message });
    setGlobalStatus('Status lookup failed.', 'error');
  } finally {
    setBusy(false);
  }
}

async function getLeaderboard() {
  const envType = getValue('leaderboard-env');
  try {
    setBusy(true);
    setGlobalStatus('Loading leaderboard...', 'info');
    const result = await getJson(`/leaderboard/${envType}`);
    showResponse('leaderboard-response', result);
    setGlobalStatus('Leaderboard loaded.', 'success');
  } catch (error) {
    showResponse('leaderboard-response', { error: error.message });
    setGlobalStatus('Leaderboard request failed.', 'error');
  } finally {
    setBusy(false);
  }
}

async function getHealth() {
  try {
    setBusy(true);
    setGlobalStatus('Checking backend health...', 'info');
    const result = await getJson('/health');
    showResponse('health-response', result);
    setGlobalStatus('Backend healthy.', 'success');
  } catch (error) {
    showResponse('health-response', { error: error.message });
    setGlobalStatus('Health check failed.', 'error');
  } finally {
    setBusy(false);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('create-task').addEventListener('click', createTask);
  document.getElementById('start-evaluation').addEventListener('click', startEvaluation);
  document.getElementById('check-status').addEventListener('click', checkStatus);
  document.getElementById('get-leaderboard').addEventListener('click', getLeaderboard);
  document.getElementById('get-health').addEventListener('click', getHealth);
});
