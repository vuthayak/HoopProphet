import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { DEBOUNCE_MS } from '../utils/constants';

export function useHitRates(playerId, stat, line) {
  const [hitRates, setHitRates] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !stat || line === undefined) return;

    const timer = setTimeout(async () => {
      let cancelled = false;
      setLoading(true);
      setError(null);

      try {
        const data = await api.getPlayerHitRates(playerId, stat, line);
        if (!cancelled) setHitRates(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => { cancelled = true; clearTimeout(timer); };
  }, [playerId, stat, line]);

  return { hitRates, loading, error };
}