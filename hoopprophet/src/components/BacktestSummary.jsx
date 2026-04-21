import { useBacktestSummary } from '../hooks/useBacktest';

export default function BacktestSummary({ data }) {
  if (!data) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-bg-card rounded-lg border border-border p-4 animate-pulse">
            <div className="h-8 bg-bg-card-hover rounded mb-2" />
            <div className="h-4 bg-bg-card-hover rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  const roi = data.roi || 0;
  const roiColor = roi >= 0 ? 'text-prob-high' : 'text-prob-low';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="bg-bg-card rounded-lg border border-border p-4">
        <div className="text-text-muted text-xs uppercase tracking-wide mb-1">Accuracy</div>
        <div className="text-2xl font-bold text-text-primary">{Math.round(data.accuracy * 100)}%</div>
      </div>
      <div className="bg-bg-card rounded-lg border border-border p-4">
        <div className="text-text-muted text-xs uppercase tracking-wide mb-1">Brier Score</div>
        <div className="text-2xl font-bold text-text-primary">{data.brier_score?.toFixed(3) || '—'}</div>
      </div>
      <div className="bg-bg-card rounded-lg border border-border p-4">
        <div className="text-text-muted text-xs uppercase tracking-wide mb-1">ROI</div>
        <div className={`text-2xl font-bold ${roiColor}`}>
          {roi >= 0 ? '+' : ''}{roi.toFixed(1)}%
        </div>
      </div>
    </div>
  );
}