import { useBacktestSummary, useBacktestSeasons, useBacktestCalibration } from '../hooks/useBacktest';
import BacktestSummaryComponent from '../components/BacktestSummary';
import SeasonBreakdown from '../components/SeasonBreakdown';
import CalibrationChart from '../components/CalibrationChart';
import SkeletonCard from '../components/skeleton/SkeletonCard';
import SkeletonTable from '../components/skeleton/SkeletonTable';

export default function BacktestPage() {
  const { data: summary, loading: summaryLoading } = useBacktestSummary();
  const { data: seasons, loading: seasonsLoading } = useBacktestSeasons();
  const { data: calibration, loading: calibLoading } = useBacktestCalibration();

  return (
    <div className="space-y-8 animate-[fadeIn_200ms_ease]">
      <h1 className="text-2xl font-bold text-text-primary">Model Accuracy</h1>

      {summaryLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <div key={i} className="h-20 bg-bg-card animate-pulse rounded-lg" />)}
        </div>
      ) : (
        <BacktestSummaryComponent data={summary} />
      )}

      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-3">Season-by-Season Breakdown</h2>
        {seasonsLoading ? <SkeletonTable rows={5} /> : <SeasonBreakdown seasons={seasons} />}
      </div>

      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-3">Calibration Chart</h2>
        {calibLoading ? (
          <div className="h-64 bg-bg-card animate-pulse rounded-lg" />
        ) : (
          <CalibrationChart data={calibration} />
        )}
      </div>
    </div>
  );
}