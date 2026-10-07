'use strict';

const REFRESH_MS = 30000;
const $ = (id) => document.getElementById(id);

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
    const response = await fetch('api/status', { cache: 'no-store' });
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

$('refresh').addEventListener('click', refresh);
refresh();
setInterval(refresh, REFRESH_MS);
