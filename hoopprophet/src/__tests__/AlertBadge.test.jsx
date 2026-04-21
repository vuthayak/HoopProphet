import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AlertBadge from '../AlertBadge';

describe('AlertBadge', () => {
  it('renders OUT alert with red styling', () => {
    render(<AlertBadge alert={{ alert_type: 'OUT', headline: 'Player out' }} />);
    expect(screen.getByText('OUT')).toBeInTheDocument();
  });

  it('renders Q for QUESTIONABLE alert', () => {
    render(<AlertBadge alert={{ alert_type: 'QUESTIONABLE', headline: 'Questionable' }} />);
    expect(screen.getByText('Q')).toBeInTheDocument();
  });

  it('renders INJ for INJURY alert', () => {
    render(<AlertBadge alert={{ alert_type: 'INJURY', headline: 'Injury' }} />);
    expect(screen.getByText('INJ')).toBeInTheDocument();
  });
});