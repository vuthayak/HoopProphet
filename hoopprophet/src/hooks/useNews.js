import { useState, useEffect } from 'react';
import { api } from '../api/client';

export function useNews(playerId) {
  const [news, setNews] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [staleWarning, setStaleWarning] = useState(null);
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

    api.getPlayerNews(playerId)
      .then(data => {
        if (!cancelled) {
          setNews(data.news_items || []);
          setAlerts(data.alerts || []);
          setStaleWarning(data.stale_warning || null);
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
  }, [playerId]);

  return { news, alerts, staleWarning, loading, error };
}