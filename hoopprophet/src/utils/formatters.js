import { PROB_THRESHOLDS } from './constants';

export function formatProbability(prob) {
  return `${Math.round(prob * 100)}%`;
}

export function formatHitRate(rate, count) {
  if (rate === null || rate === undefined) return '—';
  return `${Math.round(rate * 100)}% (${count}g)`;
}

export function formatStatName(stat) {
  return stat.charAt(0).toUpperCase() + stat.slice(1);
}

export function getProbabilityColor(prob) {
  if (prob >= PROB_THRESHOLDS.HIGH) return 'bg-prob-high';
  if (prob >= PROB_THRESHOLDS.MODERATE) return 'bg-prob-moderate';
  return 'bg-prob-low';
}

export function getProbabilityTextColor(prob) {
  return 'text-white';
}