import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import BacktestPage from '../pages/BacktestPage';

vi.mock('../hooks/useBacktest', () => ({
  useBacktestSummary: () => ({ data: null, loading: false, error: null }),
  useBacktestSeasons: () => ({ data: [], loading: false, error: null }),
  useBacktestCalibration: () => ({ data: [], loading: false, error: null }),
}));

describe('BacktestPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders model accuracy heading', () => {
    render(
      <BrowserRouter>
        <BacktestPage />
      </BrowserRouter>
    );
    expect(screen.getByText('Model Accuracy')).toBeInTheDocument();
  });

  it('renders season breakdown heading', () => {
    render(
      <BrowserRouter>
        <BacktestPage />
      </BrowserRouter>
    );
    expect(screen.getByText('Season-by-Season Breakdown')).toBeInTheDocument();
  });

  it('renders calibration chart heading', () => {
    render(
      <BrowserRouter>
        <BacktestPage />
      </BrowserRouter>
    );
    expect(screen.getByText('Calibration Chart')).toBeInTheDocument();
  });
});