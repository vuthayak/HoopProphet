import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GameLogTable from '../GameLogTable';

const mockLogs = [
  { game_id: '1', game_date: '2024-01-01', matchup: 'LAL vs GSW', wl: 'W', pts: 28, reb: 7, ast: 5, stl: 1, blk: 0, min: 32, is_dnp: false },
  { game_id: '2', game_date: '2024-01-02', matchup: 'LAL vs BOS', wl: 'L', pts: 22, reb: 6, ast: 8, stl: 0, blk: 1, min: 30, is_dnp: false },
];

describe('GameLogTable', () => {
  it('renders table with game data', () => {
    render(<GameLogTable gamelogs={mockLogs} />);
    expect(screen.getByText('LAL vs GSW')).toBeInTheDocument();
  });

  it('shows empty state for no data', () => {
    render(<GameLogTable gamelogs={[]} />);
    expect(screen.getByText(/no game logs/i)).toBeInTheDocument();
  });

  it('shows DNP indicator for is_dnp rows', () => {
    const logsWithDnp = [{ ...mockLogs[0], is_dnp: true, pts: null }];
    render(<GameLogTable gamelogs={logsWithDnp} />);
    expect(screen.getByText('DNP')).toBeInTheDocument();
  });
});