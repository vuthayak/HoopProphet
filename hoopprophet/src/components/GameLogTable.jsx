export default function GameLogTable({ gamelogs }) {
  if (!gamelogs || gamelogs.length === 0) {
    return <p className="text-text-muted text-sm">No game logs available for this player.</p>;
  }

  return (
    <div className="overflow-x-auto max-h-96 overflow-y-auto">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-bg-primary text-text-secondary">
          <tr>
            <th className="px-2 py-1 text-left">Date</th>
            <th className="px-2 py-1 text-left">Matchup</th>
            <th className="px-2 py-1 text-center">W/L</th>
            <th className="px-2 py-1 text-center">PTS</th>
            <th className="px-2 py-1 text-center">REB</th>
            <th className="px-2 py-1 text-center">AST</th>
            <th className="px-2 py-1 text-center">STL</th>
            <th className="px-2 py-1 text-center">BLK</th>
            <th className="px-2 py-1 text-center">MIN</th>
          </tr>
        </thead>
        <tbody>
          {gamelogs.map((log, i) => (
            <tr
              key={log.game_id || i}
              className={`border-b border-border hover:bg-bg-card-hover transition-colors ${log.is_dnp ? 'text-text-muted' : ''}`}
            >
              <td className="px-2 py-1.5">{log.game_date}</td>
              <td className="px-2 py-1.5">{log.matchup}</td>
              <td className="px-2 py-1.5 text-center">{log.wl || '—'}</td>
              <td className="px-2 py-1.5 text-center font-medium">{log.is_dnp ? 'DNP' : log.pts}</td>
              <td className="px-2 py-1.5 text-center">{log.is_dnp ? '—' : log.reb}</td>
              <td className="px-2 py-1.5 text-center">{log.is_dnp ? '—' : log.ast}</td>
              <td className="px-2 py-1.5 text-center">{log.is_dnp ? '—' : log.stl}</td>
              <td className="px-2 py-1.5 text-center">{log.is_dnp ? '—' : log.blk}</td>
              <td className="px-2 py-1.5 text-center">{log.is_dnp ? '—' : log.min}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}