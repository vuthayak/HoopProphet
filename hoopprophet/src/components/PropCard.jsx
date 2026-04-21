import { useState } from 'react';
import ProbabilityBadge from './ProbabilityBadge';
import LineSlider from './LineSlider';
import HitRateChart from './HitRateChart';
import { useHitRates } from '../hooks/useHitRates';
import SkeletonCard from './skeleton/SkeletonCard';

export default function PropCard({ prop, playerId }) {
  const [adjustedLine, setAdjustedLine] = useState(prop.line);
  const { hitRates, loading } = useHitRates(playerId, prop.stat, adjustedLine);

  function handleLineChange(newLine) {
    setAdjustedLine(newLine);
  }

  return (
    <div className="bg-bg-card rounded-lg border border-border p-4 hover:scale-[1.01] hover:border-slate-600 transition-all duration-150 animate-[fadeSlideUp_300ms_ease-out] min-w-[320px]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-text-primary font-medium capitalize">{prop.stat} {adjustedLine}</span>
        {prop.direction && <span className="text-xs text-text-muted">{prop.direction}</span>}
      </div>

      <div className="flex justify-center mb-4">
        <ProbabilityBadge probability={prop.probability} direction={prop.direction || 'OVER'} />
      </div>

      <div className="mb-4">
        <LineSlider
          stat={prop.stat}
          defaultLine={prop.line}
          onLineChange={handleLineChange}
        />
      </div>

      <div className="h-40">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-text-muted border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <HitRateChart data={hitRates} />
        )}
      </div>
    </div>
  );
}