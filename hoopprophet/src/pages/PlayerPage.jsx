import { useState } from 'react';
import { useParams } from 'react-router';
import { usePlayerData } from '../hooks/usePlayerData';
import { useGameLogs } from '../hooks/useGameLogs';
import { useNews } from '../hooks/useNews';
import PlayerHeader from '../components/PlayerHeader';
import TabBar from '../components/TabBar';
import PropCard from '../components/PropCard';
import GameLogTable from '../components/GameLogTable';
import NewsList from '../components/NewsList';
import SkeletonCard from '../components/skeleton/SkeletonCard';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'gamelogs', label: 'Game Logs' },
  { id: 'news', label: 'News' },
];

export default function PlayerPage() {
  const { playerId } = useParams();
  const [tab, setTab] = useState('overview');
  const { player, props, alerts, loading, error } = usePlayerData(playerId);
  const { gamelogs } = useGameLogs(playerId);
  const { news, staleWarning } = useNews(playerId);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-prob-low">Unable to load data. Check your connection and try again.</p>
      </div>
    );
  }

  if (!player) return null;

  return (
    <div className="animate-[fadeIn_200ms_ease]">
      <PlayerHeader player={player} alerts={alerts} />

      <TabBar tabs={TABS} activeTab={tab} onTabChange={setTab} />

      <div className="mt-6 transition-opacity duration-150">
        {tab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {props?.top_props?.map((prop, i) => (
              <PropCard key={i} prop={prop} playerId={playerId} />
            ))}
          </div>
        )}

        {tab === 'gamelogs' && <GameLogTable gamelogs={gamelogs} />}

        {tab === 'news' && (
          <NewsList news={news} alerts={alerts} staleWarning={staleWarning} />
        )}
      </div>
    </div>
  );
}