import React from 'react';
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useSearch } from '../hooks/useSearch';

export default function PlayerSearch() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const { query, setQuery, results, loading } = useSearch(player => {
    navigate(`/player/${player.player_id}`);
    setQuery('');
    setIsOpen(false);
  });
  const wrapperRef = useRef(null);

  useEffect(() => {
    setIsOpen(query.length >= 2 && results.length > 0);
  }, [query, results]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setQuery('');
    }
  }

  return (
    <div ref={wrapperRef} className="relative w-full">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search players..."
        aria-label="Search players"
        className="w-full px-3 py-1.5 bg-bg-primary border border-border rounded text-text-primary text-sm placeholder-text-muted focus:outline-none focus:border-accent"
      />
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-bg-card border border-border rounded shadow-lg animate-[dropdownIn_150ms_ease-out] z-50">
          {loading && <div className="px-3 py-2 text-text-muted text-sm">Loading...</div>}
          {!loading && results.length === 0 && <div className="px-3 py-2 text-text-muted text-sm">No players found</div>}
          {!loading && results.length > 0 && (
            <ul>
              {results.map(player => (
                <li key={player.player_id}>
                  <button
                    onClick={() => {
                      navigate(`/player/${player.player_id}`);
                      setQuery('');
                      setIsOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-bg-card-hover text-text-primary text-sm"
                  >
                    {player.full_name} <span className="text-text-muted">{player.position} · {player.team_id}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}