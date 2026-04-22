import React from 'react';
import { Link } from 'react-router';
import PlayerSearch from './PlayerSearch';

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-bg-card border-b border-border">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="text-prob-high font-bold text-xl">
          HoopProphet
        </Link>
        <div className="flex-1 max-w-xs mx-4">
          <PlayerSearch />
        </div>
        <Link
          to="/backtest"
          className="text-text-secondary hover:text-text-primary transition-colors text-sm"
        >
          Backtest
        </Link>
      </div>
    </nav>
  );
}