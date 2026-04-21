import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { DEBOUNCE_MS, SEARCH_MIN_CHARS } from '../utils/constants';

export function useSearch(onSelect) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (query.length < SEARCH_MIN_CHARS) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      let cancelled = false;
      setLoading(true);
      setError(null);

      try {
        const data = await api.searchPlayers(query);
        if (!cancelled) {
          setResults(data.slice(0, 10));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setResults([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return { query, setQuery, results, loading, error, onSelect };
}