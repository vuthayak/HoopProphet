import AlertBadge from './AlertBadge';

export default function PlayerHeader({ player, alerts }) {
  const imgUrl = `https://cdn.nba.com/headshots/nba/latest/1040x760/${player.player_id}.png`;

  return (
    <div className="flex items-center gap-4 mb-6">
      <img
        src={imgUrl}
        alt={player.full_name}
        className="w-[72px] h-[72px] rounded-lg object-cover bg-bg-card"
        onError={e => {
          const initials = player.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
          e.target.replaceWith(
            Object.assign(document.createElement('div'), {
              className: 'w-[72px] h-[72px] rounded-lg bg-bg-card flex items-center justify-center text-text-secondary text-xl font-bold',
              textContent: initials,
            })
          );
        }}
      />
      <div className="flex-1">
        <h1 className="text-xl font-semibold text-text-primary">{player.full_name}</h1>
        <p className="text-sm text-text-secondary">{player.position} · {player.team_id}</p>
        {alerts && alerts.length > 0 && (
          <div className="flex gap-1 mt-1">
            {alerts.slice(0, 3).map((a, i) => (
              <AlertBadge key={i} alert={a} />
            ))}
            {alerts.length > 3 && (
              <span className="text-xs text-text-muted">+{alerts.length - 3} more</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}