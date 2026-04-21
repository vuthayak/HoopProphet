export const PROB_THRESHOLDS = { HIGH: 0.65, MODERATE: 0.40 };
export const HIT_RATE_WINDOWS = ['L5', 'L10', 'L20', 'Season'];
export const HIT_RATE_COLORS = { HIGH: '#22c55e', MODERATE: '#eab308', LOW: '#ef4444' };
export const ALERT_STYLES = {
  OUT: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'OUT' },
  QUESTIONABLE: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Q' },
  INJURY: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'INJ' },
  TRADE: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'TRADE' },
  SUSPENSION: { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'SUSP' },
  G_LEAGUE: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'G' },
  REST: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'REST' },
};
export const DEBOUNCE_MS = 300;
export const SEARCH_MIN_CHARS = 2;