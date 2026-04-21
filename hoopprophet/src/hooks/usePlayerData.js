import { useState, useEffect } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';

export function usePlayerData(playerId) {
  const [player, setPlayer] = useState(null);
  const [props, setProps] = useState(null);
  const [lines, setLines] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    async function fetchAll() {
      try {
        const [playerData, propsData, linesData] = await Promise.all([
          api.getPlayer(playerId),
          api.getPlayerProps(playerId),
          api.getPlayerLines(playerId),
        ]);
        if (cancelled) return;
        setPlayer(playerData);
        setProps(propsData);
        setLines(linesData);
        setAlerts(playerData?.alerts || []);
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
        toast.error('Unable to load player data.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [playerId]);

  return { player, props, lines, alerts, loading, error };
}