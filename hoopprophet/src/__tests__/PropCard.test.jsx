import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PropCard from '../PropCard';

vi.mock('../hooks/useHitRates', () => ({
  useHitRates: () => ({ hitRates: null, loading: false })
}));

describe('PropCard', () => {
  it('renders stat name and line', () => {
    const prop = { stat: 'pts', line: 24.5, probability: 0.72, direction: 'OVER' };
    render(<PropCard prop={prop} playerId="123" />);
    expect(screen.getByText(/pts 24.5/i)).toBeInTheDocument();
  });
});