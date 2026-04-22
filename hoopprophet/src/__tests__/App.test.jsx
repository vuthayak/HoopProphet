import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router';
import App from '../App';

describe('App', () => {
  it('renders HoopProphet brand name', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByText('HoopProphet', { selector: 'a' })).toBeInTheDocument();
  });

  it('renders Backtest nav link', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByText('Backtest')).toBeInTheDocument();
  });

  it('renders home page placeholder text', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByText('Search for a player to get started')).toBeInTheDocument();
  });
});