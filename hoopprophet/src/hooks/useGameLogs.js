import { useState, useEffect } from 'react';
import { api } from '../api/client';

export function useGameLogs(playerId, limit = 50) {
  const [gamelogs, setGamelogs] = useState([]);
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

    api.getPlayerGameLogs(playerId, limit)
      .then(data => {
        if (!cancelled) {
          setGamelogs(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [playerId, limit]);

  return { gamelogs, loading, error };
}