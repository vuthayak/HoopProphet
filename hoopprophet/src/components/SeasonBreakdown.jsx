export default function SeasonBreakdown({ seasons }) {
  if (!seasons || seasons.length === 0) {
    return <p className="text-text-muted text-sm">No season data available.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-text-secondary border-b border-border">
          <tr>
            <th className="px-3 py-2 text-left">Season</th>
            <th className="px-3 py-2 text-center">Games</th>
            <th className="px-3 py-2 text-center">Accuracy</th>
            <th className="px-3 py-2 text-center">Brier</th>
            <th className="px-3 py-2 text-center">ROI</th>
          </tr>
        </thead>
        <tbody>
          {seasons.map((s, i) => {
            const roiColor = s.roi >= 0 ? 'text-prob-high' : 'text-prob-low';
            return (
              <tr key={i} className="border-b border-border hover:bg-bg-card-hover transition-colors">
                <td className="px-3 py-2">{s.season}</td>
                <td className="px-3 py-2 text-center">{s.n_games}</td>
                <td className="px-3 py-2 text-center">{Math.round(s.accuracy * 100)}%</td>
                <td className="px-3 py-2 text-center">{s.brier_score?.toFixed(3) || '—'}</td>
                <td className={`px-3 py-2 text-center font-medium ${roiColor}`}>
                  {s.roi >= 0 ? '+' : ''}{s.roi?.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}