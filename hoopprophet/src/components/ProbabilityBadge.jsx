import { PROB_THRESHOLDS } from '../utils/constants';
import { getProbabilityTextColor } from '../utils/formatters';

export default function ProbabilityBadge({ probability, direction = 'OVER' }) {
  const pct = Math.round(probability * 100);
  let bgClass = 'bg-prob-low';
  if (probability >= PROB_THRESHOLDS.HIGH) bgClass = 'bg-prob-high';
  else if (probability >= PROB_THRESHOLDS.MODERATE) bgClass = 'bg-prob-moderate';

  return (
    <div className="flex flex-col items-center justify-center animate-[badgeScale_250ms_ease-out]">
      <div className={`w-18 h-18 rounded-lg ${bgClass} flex items-center justify-center`}>
        <span className={`text-white text-2xl font-bold ${getProbabilityTextColor(probability)}`}>
          {pct}%
        </span>
      </div>
      <span className="text-xs text-text-muted mt-1">{direction}</span>
    </div>
  );
}