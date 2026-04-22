import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import HitRateChart from '../components/HitRateChart';

const mockData = {
  hit_rates: {
    L5: { rate: 0.60, count: 5 },
    L10: { rate: 0.50, count: 10 },
    L20: { rate: 0.55, count: 20 },
    Season: { rate: 0.52, count: 50 },
  }
};

describe('HitRateChart', () => {
  it('renders chart container', () => {
    render(<HitRateChart data={mockData} />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});