const API_BASE = import.meta.env.VITE_API_BASE || '';

async function fetchJSON(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  searchPlayers: (query) => fetchJSON(`/api/players?search=${encodeURIComponent(query)}&active_only=true`),
  getPlayer: (id) => fetchJSON(`/api/players/${id}`),
  getPlayerProps: (id) => fetchJSON(`/api/players/${id}/props`),
  getPlayerGameLogs: (id, limit = 50) => fetchJSON(`/api/players/${id}/gamelogs?limit=${limit}`),
  getPlayerHitRates: (id, stat, line) => fetchJSON(`/api/players/${id}/hitrates?stat=${stat}&line=${line}`),
  getPlayerLines: (id) => fetchJSON(`/api/players/${id}/lines`),
  getPlayerNews: (id) => fetchJSON(`/api/players/${id}/news`),
  getTeams: () => fetchJSON('/api/teams'),
  healthCheck: () => fetchJSON('/api/health'),
  getBacktestSummary: () => fetchJSON('/api/backtest/summary'),
  getBacktestSeasons: () => fetchJSON('/api/backtest/seasons'),
  getBacktestCalibration: () => fetchJSON('/api/backtest/calibration'),
};

export { fetchJSON };