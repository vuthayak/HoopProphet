import React from 'react';
import { useNavigate } from 'react-router';
import PlayerSearch from '../components/PlayerSearch';

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-4xl font-bold text-prob-high mb-4">HoopProphet</h1>
      <p className="text-xl text-text-secondary mb-2">Search for a player to get started</p>
      <p className="text-text-muted mb-8 max-w-md">
        Enter a player name above to see their prop predictions and hit rates.
      </p>
      <div className="w-full max-w-md">
        <PlayerSearch />
      </div>
    </div>
  );
}