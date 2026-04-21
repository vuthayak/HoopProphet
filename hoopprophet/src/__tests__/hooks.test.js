import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { useSearch } from '../hooks/useSearch';
import PlayerSearch from '../components/PlayerSearch';

vi.mock('../hooks/useSearch');

describe('PlayerSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders search input', () => {
    useSearch.mockReturnValue({
      query: '',
      setQuery: vi.fn(),
      results: [],
      loading: false,
      error: null,
      onSelect: vi.fn(),
    });

    render(
      <BrowserRouter>
        <PlayerSearch />
      </BrowserRouter>
    );

    expect(screen.getByPlaceholderText('Search players...')).toBeInTheDocument();
  });
});