import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProbabilityBadge from '../ProbabilityBadge';

describe('ProbabilityBadge', () => {
  it('renders 72% with green bg for probability >= 0.65', () => {
    render(<ProbabilityBadge probability={0.72} />);
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('OVER')).toBeInTheDocument();
  });

  it('renders 50% with yellow bg for probability between 0.40 and 0.65', () => {
    render(<ProbabilityBadge probability={0.50} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders 30% with red bg for probability < 0.40', () => {
    render(<ProbabilityBadge probability={0.30} />);
    expect(screen.getByText('30%')).toBeInTheDocument();
  });
});