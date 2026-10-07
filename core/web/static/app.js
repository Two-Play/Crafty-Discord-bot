'use strict';

const REFRESH_MS = 30000;
const $ = (id) => document.getElementById(id);
// Built from location.origin, which never contains credentials: fetch() refuses relative URLs when the
// page was opened as http://user:password@host/.
const api = (path) => new URL(path, location.origin + location.pathname).href;

function formatDuration(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function badge(server) {
  if (server.error) return ['error', 'unknown'];
  if (server.state === 'crashed') return ['error', 'crashed'];
  if (server.state) return ['busy', server.state];
  return server.running ? ['online', 'online'] : ['offline', 'offline'];
}

function players(server) {
  if (!server.running) return '–';
  if (server.players === null) return 'unknown';
  return server.max_players ? `${server.players} / ${server.max_players}` : String(server.players);
}

function renderServer(server) {
  const node = $('server-template').content.cloneNode(true);
  const [kind, label] = badge(server);
  const text = (selector, value) => { node.querySelector(selector).textContent = value; };

  text('.name', server.name);
  const badgeNode = node.querySelector('.badge');
  badgeNode.textContent = label;
  badgeNode.classList.add(kind);
  text('.players', players(server));
  text('.version', server.version || '–');
  text('.cpu', server.cpu === null ? '–' : `${server.cpu}%`);
  text('.memory', server.memory === null ? '–' : `${server.memory} (${server.memory_percent}%)`);
  text('.address', server.address || '–');
  text('.id', server.id);
  text('.player-names', server.error || (server.player_names.length ? server.player_names.join(', ') : ''));
  return node;
}

function render(data) {
  const bot = data.bot;
  $('bot-connected').textContent = bot.connected ? 'connected' : 'disconnected';
  $('bot-user').textContent = bot.user || '–';
  $('bot-latency').textContent = bot.latency_ms === null ? '–' : `${bot.latency_ms} ms`;
  $('bot-guilds').textContent = bot.guilds;
  $('bot-uptime').textContent = formatDuration(bot.uptime_seconds);
  $('bot-autostop').textContent = bot.auto_stop ? `every ${formatDuration(bot.auto_stop)}` : 'off';
  $('version').textContent = bot.version;

  $('error').hidden = !data.error;
  $('error').textContent = data.error || '';

  $('servers').replaceChildren(...data.servers.map(renderServer));
  $('empty').hidden = Boolean(data.error) || data.servers.length > 0;
  $('updated').textContent = `Updated ${new Date(data.updated).toLocaleTimeString()}`;
}

async function refresh() {
  const button = $('refresh');
  button.disabled = true;
  try {
    const response = await fetch(api('api/status'), { cache: 'no-store' });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${response.status}`);
    }
    render(await response.json());
  } catch (error) {
    $('error').hidden = false;
    $('error').textContent = `Could not load the status: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function showFlagError(message) {
  $('flags-error').hidden = !message;
  $('flags-error').textContent = message || '';
}

async function setFlag(name, enabled, input) {
  input.disabled = true;
  try {
    const response = await fetch(api(`api/flags/${encodeURIComponent(name)}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Crafty-Bot': '1' },
      body: JSON.stringify({ enabled }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    showFlagError(null);
    renderFlags(body);
    refresh();
  } catch (error) {
    input.checked = !enabled;
    input.disabled = false;
    showFlagError(`Could not change ${name}: ${error.message}`);
  }
}

function renderFlags(data) {
  $('flags-hint').hidden = data.editable;
  $('flags').replaceChildren(...data.flags.map((flag) => {
    const node = $('flag-template').content.cloneNode(true);
    node.querySelector('.flag-label').textContent = flag.label;
    node.querySelector('.flag-description').textContent = flag.description;
    const input = node.querySelector('input');
    input.checked = flag.enabled;
    input.disabled = !data.editable;
    input.setAttribute('aria-label', flag.label);
    input.addEventListener('change', () => setFlag(flag.name, input.checked, input));
    return node;
  }));
}

async function loadFlags() {
  try {
    const response = await fetch(api('api/flags'), { cache: 'no-store' });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    showFlagError(null);
    renderFlags(body);
  } catch (error) {
    showFlagError(`Could not load the feature flags: ${error.message}`);
  }
}

const LOG_REFRESH_MS = 5000;
const MAX_LOG_ENTRIES = 1000;
const LEVEL_ORDER = { DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50 };
const logState = { entries: [], lastId: 0, level: null };

function showLogsError(message) {
  $('logs-error').hidden = !message;
  $('logs-error').textContent = message || '';
}

function logEntryNode(entry) {
  const row = document.createElement('div');
  row.className = `log-entry ${entry.level}`;
  const cell = (className, text) => {
    const span = document.createElement('span');
    span.className = className;
    span.textContent = text;
    row.append(span);
  };
  cell('log-time', new Date(entry.time).toLocaleTimeString());
  cell('log-level', entry.level);
  cell('log-logger', entry.logger);
  row.lastChild.title = entry.logger;
  cell('log-message', entry.message);
  return row;
}

function renderLogs() {
  const box = $('logs');
  const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  const minLevel = LEVEL_ORDER[$('log-filter').value];
  const search = $('log-search').value.trim().toLowerCase();
  const visible = logState.entries.filter((entry) => (LEVEL_ORDER[entry.level] || 0) >= minLevel
    && (!search || entry.message.toLowerCase().includes(search) || entry.logger.toLowerCase().includes(search)));

  if (visible.length) {
    box.replaceChildren(...visible.map(logEntryNode));
  } else {
    const empty = document.createElement('p');
    empty.className = 'logs-empty';
    empty.textContent = logState.entries.length ? 'No log entries match the filter.' : 'No log entries yet.';
    box.replaceChildren(empty);
  }
  if (atBottom) box.scrollTop = box.scrollHeight;
}

function renderLogLevel(data) {
  const select = $('log-level');
  if (!select.options.length) {
    select.replaceChildren(...data.levels.map((level) => new Option(level, level)));
  }
  if (document.activeElement !== select) select.value = data.level;
  select.disabled = !data.editable;
  logState.level = data.level;
  $('log-level-hint').textContent = data.editable
    ? 'Changing the log level lasts until the bot restarts, then LOG_LEVEL applies again. Libraries never log below INFO.'
    : 'Set WEB_PASSWORD to change the log level here.';
}

async function loadLogs() {
  try {
    const response = await fetch(api(`api/logs?after=${logState.lastId}`), { cache: 'no-store' });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    showLogsError(null);
    renderLogLevel(body);
    if (body.entries.length || !logState.lastId) {
      logState.entries = logState.entries.concat(body.entries).slice(-MAX_LOG_ENTRIES);
      logState.lastId = body.entries.length ? body.entries[body.entries.length - 1].id : logState.lastId;
      renderLogs();
    }
  } catch (error) {
    showLogsError(`Could not load the logs: ${error.message}`);
  }
}

async function setLogLevel(level) {
  const select = $('log-level');
  select.disabled = true;
  try {
    const response = await fetch(api('api/log-level'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Crafty-Bot': '1' },
      body: JSON.stringify({ level }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    showLogsError(null);
    logState.level = body.level;
    loadLogs();
  } catch (error) {
    select.value = logState.level;
    showLogsError(`Could not change the log level: ${error.message}`);
  } finally {
    select.disabled = false;
  }
}

$('log-level').addEventListener('change', (event) => setLogLevel(event.target.value));
$('log-filter').addEventListener('change', renderLogs);
$('log-search').addEventListener('input', renderLogs);

$('refresh').addEventListener('click', () => { refresh(); loadFlags(); loadLogs(); });
refresh();
loadFlags();
loadLogs();
setInterval(loadLogs, LOG_REFRESH_MS);
setInterval(refresh, REFRESH_MS);
