import AlertBadge from './AlertBadge';

export default function NewsList({ news, alerts, staleWarning }) {
  return (
    <div className="space-y-3">
      {staleWarning && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-2 text-sm text-yellow-400">
          {staleWarning}
        </div>
      )}

      {!news || news.length === 0 ? (
        <p className="text-text-muted text-sm">No recent news or injury reports for this player.</p>
      ) : (
        news.map((item, i) => (
          <div key={i} className="bg-bg-card rounded-lg p-4 border-b border-border">
            {item.alerts && item.alerts.length > 0 && (
              <div className="flex gap-1 mb-2">
                {item.alerts.map((a, j) => <AlertBadge key={j} alert={a} />)}
              </div>
            )}
            <p className="text-text-primary text-sm font-medium mb-1">{item.headline}</p>
            <p className="text-text-muted text-xs">
              {item.source}{item.updated_ago ? ` · ${item.updated_ago}` : ''}
            </p>
          </div>
        ))
      )}
    </div>
  );
}