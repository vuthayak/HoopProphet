# Phase 7: Frontend Rebuild - Research

**Researched:** 2026-04-21
**Domain:** React SPA with Vite, Tailwind CSS, React Router, Visx charts
**Confidence:** HIGH

## Summary

Phase 7 replaces the monolithic 590-line V1 `App.js` (CRA + MUI + framer-motion) with a clean, component-based React SPA built on Vite, React Router, Tailwind CSS v4, and Visx for chart visualization. The app consumes Phase 5/6 API endpoints (`/api/players`, `/api/players/{id}/props`, `/api/players/{id}/hitrates`, etc.) and renders player prop cards with ML probability badges, hit rate bar charts, adjustable lines via sliders, game log tables, and news/injury alert badges.

The key architectural shift from V1 is: CRA → Vite (faster builds, better HMR, modern ESM), MUI → Tailwind CSS (dark-mode native utility classes eliminate theme boilerplate), monolithic component → feature-based folder structure with React Router for SPA routing, and no chart library → Visx for lightweight, composable SVG bar charts for hit rate visualization. Visx v4 alpha (React 19 compatible) must be used since the stable v3 only supports React ≤18.

**Primary recommendation:** Use React 19 + Vite 8 + Tailwind CSS v4 (with `@tailwindcss/vite` plugin) + React Router v7 (library mode) + Visx v4 alpha (@next tag) for React 19 compatibility. Dark-mode-only approach maps directly to Tailwind's `dark:` variant with a single `dark` class on `<html>`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Client-side SPA routing with React Router — / (home/search), /player/:id, /backtest
- **D-02:** Local state management (useState/useEffect) with fetch calls. No external state library.
- **D-03:** Feature-based folder structure: `pages/`, `components/` (PropCard, HitRateChart, GameLogTable, PlayerSearch, AlertBadge)
- **D-04:** MUI removed entirely. Custom design system with Tailwind CSS — dark-mode native, compact cards, probability color coding, data-dashboard aesthetics. Design details delegated to design skill.
- **D-05:** Dark mode only. No light theme toggle.
- **D-06:** Hit rate visualization as separate chart section per prop card (not inline bars). Each prop card has its own Visx bar chart showing L5/L10/L20/Season hit rates.
- **D-07:** ML probability displayed as large color-coded percentage badge (green=high, yellow=moderate, red=low).
- **D-08:** Adjustable stat lines via half-point slider per prop card.
- **D-09:** Polished micro-transitions for page loads and data refreshes (fade/slide, not flashy).
- **D-10:** Compact grid layout: 2-3 per row desktop, 1 per row mobile. Desktop-first responsive.
- **D-11:** Game log table as compact scrollable table below prop cards on player page.
- **D-12:** Injury/news alerts as colored badges next to player name (red=OUT, yellow=QUESTIONABLE, orange=INJURY). Hover for details.
- **D-13:** Three pages: Home (search landing), Player (tabs: Overview/Game Logs/News), Backtest (model accuracy dashboard).
- **D-14:** Player page uses tabbed layout.
- **D-15:** Persistent top navbar with logo, autocomplete search input, and nav links.
- **D-16:** Data fetched on-demand per page load. Promise.all for parallel fetches. No app-level prefetching.
- **D-17:** Backtest page: summary stats → season-by-season table → calibration chart.
- **D-18:** Home page: "Search for a player to get started" with prominent search input.
- **D-19:** Skeleton placeholders for loading. Toast notifications for errors.
- **D-20:** Clean rebuild from scratch. Delete all V1 frontend code.
- **D-21:** Migrate from CRA to Vite.
- **D-22:** Desktop-first responsive design: desktop (>1024px), tablet (768-1024px), mobile (<768px).
- **D-23:** React Testing Library for component tests.

### the agent's Discretion
- Exact Tailwind design tokens (colors, spacing, typography)
- Visx chart styling details (axis formatting, bar colors, animation timing)
- Skeleton placeholder shapes and timing
- Toast notification library choice (react-hot-toast, react-toastify, or custom)
- Router guard/hook patterns for data loading
- Exact responsive breakpoint values
- Component internal state patterns

### Deferred Ideas (OUT OF SCOPE)
- Daily picks dashboard (PICK-01/02/03)
- League-wide leaderboard or comparison views
- User accounts / authentication
- Mobile app or PWA
- Light theme toggle
- Push notifications for news alerts
- Sportsbook odds comparison (ODDS-01/02/03)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Component-based architecture (pages, components, hooks — not monolithic App.js) | Vite project scaffolding + folder structure pattern (§Architecture Patterns) |
| UI-02 | Autocomplete player search | React Router SPA + fetch `/api/players?search=` endpoint (§Code Examples) |
| UI-03 | Prop cards with hit rate charts, ML probability, adjustable lines | Visx Bar component + Tailwind card layout + slider pattern (§Code Examples) |
| UI-04 | Game log table | Tailwind table styling + fetch `/api/players/{id}/gamelogs` (§Code Examples) |
| UI-05 | News/injury flags on player page | Alert badge component + fetch `/api/players/{id}/news` (§Architecture Patterns) |
| UI-06 | Back-test page showing model accuracy and calibration metrics | Visx chart for calibration + Tailwind dashboard layout (§Architecture Patterns) |
| UI-07 | Clean, modern, data-focused dashboard design | Tailwind CSS dark-mode design system (§Architecture Patterns) |
| UI-08 | Bar charts for hit rates across L5/L10/L20/season windows | Visx Bar + scaleBand/scaleLinear + ParentSize responsive (§Code Examples) |
| PROP-03 | Adjustable stat lines via slider | Tailwind + custom half-point slider component (§Code Examples) |
| PROP-02 | Default stat lines from player performance | Fetch `/api/players/{id}/lines` + `/api/players/{id}/props` (§Architecture Patterns) |
| NEWS-03 | News flags visible on player page | Alert badge component pattern (§Architecture Patterns) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Player search autocomplete | Browser / Client | API (data source) | Search UI runs in browser; API provides player list |
| Prop card rendering with probability badges | Browser / Client | — | Pure client-side rendering of API data |
| Hit rate bar charts (Visx) | Browser / Client | — | SVG rendering in browser; data from API |
| Adjustable line slider交互 | Browser / Client | API (hit rate recomputation) | Slider UI in browser; triggers hit rate fetch when line changes |
| Game log table display | Browser / Client | API (data source) | Table rendering in browser; paginated data from API |
| News/injury alert badges | Browser / Client | API (data source) | Badge rendering in browser; alerts from API |
| SPA routing (Home / Player / Backtest) | Browser / Client | — | React Router runs entirely client-side |
| Dark mode styling | Browser / Client | — | Tailwind dark: utility classes, no server involvement |
| API proxy (dev) | Frontend Server (Vite dev) | — | Vite dev server proxies /api/* to backend:8000 |
| Static build serving (prod) | CDN / Static | — | Vite build output served as static files via Docker |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.1.0 | UI framework | Project already uses React 19 (locked in V1 package.json). Latest stable. [VERIFIED: npm registry] |
| react-dom | ^19.1.0 | React DOM renderer | Required pair for React 19. [VERIFIED: npm registry] |
| react-router | ^7.14.2 | SPA client-side routing | React Router v7 is the current major version. Supports `createBrowserRouter` for data routing, but we use simple declarative `<Routes>` / `<Route>` for library mode. [VERIFIED: npm registry] |
| vite | ^8.0.9 | Build tool + dev server | Replaces CRA. Faster HMR, ESM-native, smaller bundles. Latest stable. [VERIFIED: npm registry] |
| @vitejs/plugin-react | ^6.0.1 | Vite React plugin (Oxc transform) | Fast Refresh support for React components in Vite. [VERIFIED: npm registry] |
| tailwindcss | ^4.2.4 | Utility-first CSS framework | Tailwind v4 native dark mode, no config file needed (CSS-first config). Install via `@tailwindcss/vite` plugin. [VERIFIED: npm registry] |
| @tailwindcss/vite | ^4.2.4 | Tailwind v4 Vite plugin | First-class Vite integration for Tailwind v4. Eliminates PostCSS config. [VERIFIED: npm registry] |
| @visx/shape | 4.0.0-alpha.11 | SVG Bar and shape primitives for charts | Bar component for hit rate charts. Must use v4 alpha for React 19 support. [VERIFIED: npm registry @next tag] |
| @visx/group | 4.0.0-alpha.11 | SVG Group container for chart composition | Wraps chart elements for positioning. [VERIFIED: npm registry @next tag] |
| @visx/scale | 4.0.0-alpha.11 | D3-based scale functions (scaleBand, scaleLinear) | Required for bar chart axis scales. [VERIFIED: npm registry @next tag] |
| @visx/axis | 4.0.0-alpha.11 | Axis rendering for charts | Chart axes (L5/L10/L20/Season labels). [VERIFIED: npm registry @next tag] |
| @visx/responsive | 4.0.0-alpha.11 | ParentSize for responsive chart containers | Charts resize with their container. [VERIFIED: npm registry @next tag] |
| @visx/gradient | 4.0.0-alpha.11 | Gradient fills for bar charts | Visual polish on chart bars. [VERIFIED: npm registry @next tag] |
| @visx/tooltip | 4.0.0-alpha.11 | Tooltips for bar chart hover interactions | Show exact hit rate values on bar hover. [VERIFIED: npm registry @next tag] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @testing-library/react | ^16.3.2 | Component testing (render, interact, assert) | All component tests per D-23 |
| @testing-library/jest-dom | ^6.9.1 | DOM matchers for tests (toBeInTheDocument, etc.) | Component test assertions |
| @testing-library/user-event | ^14.6.1 | Simulate user interactions in tests | Slider, search input, tab click tests |
| vitest | ^3.2.5 | Test runner optimized for Vite | Replaces CRA test runner (jest). Native ESM support, faster. |
| jsdom | ^26.1.0 | DOM environment for Vitest | Required for component tests that need DOM APIs |
| react-hot-toast | ^2.6.0 | Lightweight toast notification library | Error toasts per D-19. 5KB gzipped, simple API, customizable. [ASSUMED: training knowledge on size, verified npm version] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|-----------|-----------|----------|
| react-hot-toast | react-toastify | react-toastify is more feature-rich but larger bundle. react-hot-toast is simpler and lighter — matches our "data dashboard" aesthetic better. |
| Vitest | Jest (via vitest-jest compat) | Vitest is native to Vite, uses same config, faster transforms. Jest requires additional CRA eject config. |
| React Router v7 (framework mode) | React Router v7 (library mode) | Framework mode requires SSR and a build-time server. Library mode gives us simple client-side routing with `<BrowserRouter>` — matches our SPA architecture. |
| Recharts | Visx | Recharts is higher-level and easier to get started, but Visx gives pixel-level control over chart composition with smaller bundle (tree-shakeable). For 4-bar grouped charts (L5/L10/L20/Season), Visx's composability is better. |
| D3 directly | Visx | D3 requires imperative DOM manipulation. Visx wraps D3 computations in React components — prevents "two mental models" problem. |

**Installation:**
```bash
# Core
npm install react@^19.1.0 react-dom@^19.1.0 react-router@^7.14.2

# Build toolchain
npm install -D vite@^8.0.9 @vitejs/plugin-react@^6.0.1

# Styling
npm install -D tailwindcss@^4.2.4 @tailwindcss/vite@^4.2.4

# Charts (v4 alpha for React 19 support)
npm install @visx/shape@next @visx/group@next @visx/scale@next @visx/axis@next @visx/responsive@next @visx/gradient@next @visx/tooltip@next

# Testing
npm install -D vitest@^3.2.5 jsdom@^26.1.0 @testing-library/react@^16.3.2 @testing-library/jest-dom@^6.9.1 @testing-library/user-event@^14.6.1

# Toasts
npm install react-hot-toast@^2.6.0
```

**Version verification:**
- React 19.1.0 → verified npm registry (latest 19.x as of 2026-04-21)
- Vite 8.0.9 → verified npm registry (latest stable)
- Tailwind CSS 4.2.4 → verified npm registry (latest stable)
- React Router 7.14.2 → verified npm registry (latest stable)
- Visx 4.0.0-alpha.11 → verified npm @next tag (only version with React 19 peer dep)

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                  Browser / Client                │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │            React Router (SPA)               │ │
│  │  / → HomePage                               │ │
│  │  /player/:id → PlayerPage                   │ │
│  │  /backtest → BacktestPage                   │ │
│  └────────────────┬────────────────────────────┘ │
│                   │                               │
│  ┌────────────────┴────────────────────────────┐ │
│  │           Page Components                    │ │
│  │  HomePage   PlayerPage   BacktestPage         │ │
│  │    │            │             │              │ │
│  │    ▼            ▼             ▼              │ │
│  │  PlayerSearch  PropCard    CalibChart        │ │
│  │  (autocomplete)(+ HitRateChart)(Visx)      │ │
│  │                GameLogTable                  │ │
│  │                AlertBadge                    │ │
│  └────────────────┬────────────────────────────┘ │
│                   │                               │
│          fetch() / api calls                      │
│                   │                               │
│  ┌────────────────┴────────────────────────────┐ │
│  │         Vite Dev Server Proxy               │ │
│  │  /api/* → http://localhost:8000/*            │ │
│  └────────────────┬────────────────────────────┘ │
└────────────────────┼──────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│            FastAPI Backend (:8000)               │
│                                                   │
│  /api/players           → PlayerService          │
│  /api/players/{id}      → PlayerService          │
│  /api/players/{id}/props → PredictionService     │
│  /api/players/{id}/hitrates → HitRateService     │
│  /api/players/{id}/gamelogs → PlayerService      │
│  /api/players/{id}/lines → PredictionService     │
│  /api/players/{id}/news → NewsService            │
│  /api/teams             → TeamService             │
│  /api/health            → Health check            │
│                                                   │
│  SQLite cache ← Pipeline data (Phase 1-2)        │
│  Model artifact ← Training output (Phase 3)      │
└───────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/
├── main.jsx                  # React 19 entry point (createRoot)
├── App.jsx                   # Router setup, global layout, navbar
├── index.css                 # Tailwind v4 imports + custom theme
├── pages/
│   ├── HomePage.jsx           # Search landing page (D-18)
│   ├── PlayerPage.jsx          # Tabbed player analysis (D-13, D-14)
│   └── BacktestPage.jsx        # Model accuracy dashboard (D-17)
├── components/
│   ├── Navbar.jsx              # Persistent top nav with logo + search + links (D-15)
│   ├── PlayerSearch.jsx        # Autocomplete search input (UI-02)
│   ├── PropCard.jsx            # Single prop card with probability badge (D-07)
│   ├── HitRateChart.jsx        # Visx bar chart per prop card (D-06, UI-08)
│   ├── LineSlider.jsx          # Half-point adjustable line slider (D-08, PROP-03)
│   ├── GameLogTable.jsx        # Compact scrollable game log table (D-11, UI-04)
│   ├── AlertBadge.jsx          # Colored injury/news badge (D-12, UI-05)
│   ├── ProbabilityBadge.jsx    # Color-coded ML probability display (D-07)
│   ├── SkeletonCard.jsx        # Skeleton placeholder for loading (D-19)
│   └── ToastProvider.jsx        # react-hot-toast wrapper (D-19)
├── hooks/
│   ├── usePlayer.js            # Fetch player details + alerts
│   ├── usePlayerProps.js        # Fetch props with hit rates
│   ├── usePlayerGameLogs.js     # Fetch game logs
│   ├── usePlayerNews.js         # Fetch news/alerts
│   └── useHitRates.js           # Fetch hit rates for adjusted line
└── api/
    └── client.js              # Base fetch wrapper, API_BASE config
```

### Pattern 1: Vite + React + Tailwind CSS v4 Setup
**What:** Build toolchain replacing CRA with Vite, styling with Tailwind v4 (CSS-first config)
**When to use:** Project initialization (replacing `hoopprophet/src/` entirely)
**Example:**
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

```css
/* src/index.css — Tailwind v4 CSS-first configuration */
@import "tailwindcss";

/* Dark mode only: override dark variant to use .dark class on <html> */
@custom-variant dark (&:where(.dark, .dark *));

/* Custom theme: probability colors */
@theme {
  --color-prob-high: #22c55e;    /* green-500 */
  --color-prob-moderate: #eab308; /* yellow-500 */
  --color-prob-low: #ef4444;     /* red-500 */
  --color-bg-primary: #0f172a;   /* slate-900 */
  --color-bg-card: #1e293b;      /* slate-800 */
  --color-bg-card-hover: #334155; /* slate-700 */
  --color-text-primary: #f8fafc;  /* slate-50 */
  --color-text-secondary: #94a3b8; /* slate-400 */
  --color-border: #334155;       /* slate-700 */
}
```
*Source: [CITED: tailwindcss.com/docs/installation — Vite plugin setup], [CITED: tailwindcss.com/docs/dark-mode — @custom-variant]*

### Pattern 2: React Router v7 Library Mode (SPA)
**What:** Client-side-only routing with declarative route definitions
**When to use:** Three-page SPA (D-01, D-13)
**Example:**
```jsx
// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router';
import HomePage from './pages/HomePage';
import PlayerPage from './pages/PlayerPage';
import BacktestPage from './pages/BacktestPage';
import Navbar from './components/Navbar';

function App() {
  return (
    <BrowserRouter>
      <div className="dark min-h-screen bg-bg-primary text-text-primary">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/player/:playerId" element={<PlayerPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```
*Source: [CITED: react-router v7 docs — createBrowserRouter, Routes, Route]*

### Pattern 3: Data Fetching with Local State
**What:** useState + useEffect + fetch per page component, no external state library (D-02)
**When to use:** All page-level data fetching
**Example:**
```jsx
// src/hooks/usePlayerProps.js
import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export function usePlayerProps(playerId) {
  const [props, setProps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId) return;
    
    let cancelled = false;
    setLoading(true);
    
    fetch(`${API_BASE}/api/players/${playerId}/props`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (!cancelled) {
          setProps(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    
    return () => { cancelled = true; };
  }, [playerId]);

  return { props, loading, error };
}
```
*Source: [ASSUMED — standard React pattern, adapted for project API]*

### Pattern 4: Visx Hit Rate Bar Chart
**What:** Grouped bar chart showing L5/L10/L20/Season hit rates per prop
**When to use:** HitRateChart component inside each PropCard (D-06, UI-08)
**Example:**
```jsx
// src/components/HitRateChart.jsx
import { ParentSize } from '@visx/responsive';
import { Group } from '@visx/group';
import { Bar } from '@visx/shape';
import { scaleBand, scaleLinear } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';

const WINDOWS = ['L5', 'L10', 'L20', 'Season'];
const BAR_COLORS = ['#60a5fa', '#34d399', '#f59e0b', '#a78bfa'];

function HitRateChartInner({ width, height, hitRates }) {
  const margin = { top: 10, right: 10, bottom: 30, left: 40 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const data = WINDOWS.map((w, i) => ({
    label: w,
    rate: hitRates[w]?.rate ?? 0,
    count: hitRates[w]?.count ?? 0,
    fill: BAR_COLORS[i],
  }));

  const xScale = scaleBand({
    range: [0, innerWidth],
    domain: data.map(d => d.label),
    padding: 0.3,
  });

  const yScale = scaleLinear({
    range: [innerHeight, 0],
    domain: [0, 1],
  });

  return (
    <svg width={width} height={height}>
      <Group top={margin.top} left={margin.left}>
        {data.map((d) => {
          const barHeight = innerHeight - yScale(d.rate);
          return (
            <Bar
              key={d.label}
              x={xScale(d.label)}
              y={innerHeight - barHeight}
              width={xScale.bandwidth()}
              height={barHeight}
              fill={d.fill}
              rx={4}
            />
          );
        })}
        <AxisBottom
          top={innerHeight}
          scale={xScale}
          stroke="#94a3b8"
          tickStroke="#94a3b8"
          tickLabelProps={() => ({
            fill: '#94a3b8',
            fontSize: 11,
            textAnchor: 'middle',
          })}
        />
        <AxisLeft
          scale={yScale}
          stroke="#94a3b8"
          tickStroke="#94a3b8"
          tickLabelProps={() => ({
            fill: '#94a3b8',
            fontSize: 11,
            textAnchor: 'end',
          })}
          tickFormat={(v) => `${Math.round(v * 100)}%`}
        />
      </Group>
    </svg>
  );
}

export default function HitRateChart({ hitRates, height = 160 }) {
  return (
    <div style={{ width: '100%', height }}>
      <ParentSize debounceTime={50}>
        {({ width }) => width > 0
          ? <HitRateChartInner width={width} height={height} hitRates={hitRates} />
          : null
        }
      </ParentSize>
    </div>
  );
}
```
*Source: [CITED: airbnb/visx README — Bar Graph example], [CITED: @visx/responsive docs — ParentSize]*

### Pattern 5: Dark-Mode-Only Approach with Tailwind v4
**What:** Single dark theme, no toggle. The `dark` class is always present on `<html>`.
**When to use:** All styling throughout the app (D-05)
**Example:**
```html
<!-- index.html -->
<html class="dark">
  <body class="bg-slate-900 text-slate-50">
    <!-- All content is dark by default -->
  </body>
</html>
```

```css
/* src/index.css */
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --color-bg-primary: #0f172a;   /* slate-900 */
  --color-bg-card: #1e293b;      /* slate-800 */
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
}
```

```jsx
// Example: PropCard dark-mode styling
<div className="bg-bg-card rounded-lg p-4 border border-border hover:bg-bg-card-hover transition-colors">
  <ProbabilityBadge probability={0.78} /> {/* green-500 bg */}
  <HitRateChart hitRates={prop.hit_rates} />
</div>
```
*Source: [CITED: tailwindcss.com/docs/dark-mode — @custom-variant]*
*[ASSUMED: color palette values — design skill will finalize exact tokens]*

### Anti-Patterns to Avoid
- **Anti-pattern: Importing MUI components** — V1 used MUI. V2 must NOT import any MUI/@mui packages. Remove all MUI dependencies. (D-04)
- **Anti-pattern: useEffect without cleanup** — Every fetch hook must have a `cancelled` flag or AbortController to prevent stale state updates on unmount.
- **Anti-pattern: Single App.js monolith** — V1 was 590 lines. V2 must be decomposed into pages/, components/, hooks/ (D-03, UI-01).
- **Anti-pattern: CRA proxy config** — V2 uses Vite. API proxy goes in `vite.config.js`, not `package.json`. The env var changes from `REACT_APP_API_BASE` to `VITE_API_BASE`.
- **Anti-pattern: Inline SVG chart dimensions** — Visx charts MUST use `ParentSize` wrapper for responsive behavior. Fixed width/height charts won't resize for mobile (D-10, D-22).
- **Anti-pattern: Installing Visx v3** — Visx v3 only has React ≤18 peer dependency. Must use `@next` tag (v4 alpha) for React 19 compatibility.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart rendering | Custom canvas/SVG bars from scratch | @visx/shape + @visx/scale | Axis rendering, band scales, hover interactions, and responsive resize all solved. Custom SVG = hundreds of lines for edge cases. |
| CSS reset + dark theme | Manual CSS reset + custom properties | Tailwind v4 Preflight + @theme | Tailwind's Preflight normalizes cross-browser. `@theme` block handles custom design tokens. |
| Bunding + HMR | Webpack config or CRA eject | Vite + @vitejs/plugin-react | Vite provides 10-100x faster HMR and native ESM. CRA is deprecated. |
| Routing | Manual hash routing or window.history | React Router v7 `<BrowserRouter>` | Browser history, nested routes, route params, and 404 handling all built-in. |
| Toast notifications | Custom div overlay + timeout | react-hot-toast | Accessible, animated, positionable, 5KB. Custom solution = reinventing accessibility. |
| Responsive breakpoints | Custom media queries | Tailwind responsive prefixes (md:, lg:) | Consistent with design system, no CSS file sprawl. |

**Key insight:** This project's UI is fundamentally a data dashboard with charts. Visx's composability (separate @visx/shape, @visx/scale, @visx/axis packages) means we only bundle what we need — unlike Recharts or Chart.js which bundle everything. For a 4-bar grouped chart per prop card, Visx's low-level primitives give precise control without bloated bundles.

## Common Pitfalls

### Pitfall 1: Visx v3 React 19 Incompatibility
**What goes wrong:** Installing `@visx/shape@latest` (v3.12.0) results in React ≤18 peer dependency. React 19 will cause peer dep warnings or runtime errors with `createRoot`.
**Why it happens:** Visx v3 stable was released before React 19. The v4 alpha with React 19 support is only available via the `@next` tag.
**How to avoid:** Install ALL Visx packages with `@next` tag: `npm install @visx/shape@next @visx/group@next @visx/scale@next @visx/axis@next @visx/responsive@next @visx/gradient@next @visx/tooltip@next`.
**Warning signs:** `npm warn peer dep` warnings about React version; `createRoot` errors in console.

### Pitfall 2: CRA Environment Variable Migration
**What goes wrong:** Using `process.env.REACT_APP_API_BASE` in Vite code — it will be `undefined`.
**Why it happens:** Vite uses `import.meta.env.VITE_*` instead of CRA's `process.env.REACT_APP_*`.
**How to avoid:** Change all env vars to `VITE_` prefix. The Vite config proxies `/api` in dev, but the env var is needed for Docker/prod: `VITE_API_BASE`.
**Warning signs:** API calls return network errors because base URL is empty string.

### Pitfall 3: Tailwind v4 CSS-First Configuration Confusion
**What goes wrong:** Trying to create `tailwind.config.js` or `tailwind.config.ts` — Tailwind v4 eliminated config files in favor of CSS-first configuration via `@theme` directives.
**Why it happens:** Most tutorials and Stack Overflow answers reference Tailwind v3 config-file approach.
**How to avoid:** All customization goes in `src/index.css` using `@theme { }` blocks. No `tailwind.config.js` file. Use `@custom-variant` for dark mode class selector. Use `@tailwindcss/vite` plugin instead of PostCSS config.
**Warning signs:** Build errors about missing PostCSS config, or utility classes not generating.

### Pitfall 4: Visx Chart Dimensions Not Responsive
**What goes wrong:** Charts render at fixed size and overflow/clip on mobile.
**Why it happens:** Visx components require explicit `width` and `height` props — they don't auto-size from their container.
**How to avoid:** Every chart component MUST be wrapped in `<ParentSize>` from `@visx/responsive`. The `ParentSize` render prop provides dynamic `width` and `height` that resize with the container.
**Warning signs:** Charts clipped on the right side, or invisible on narrow screens.

### Pitfall 5: React Router v7 Framework vs Library Mode
**What goes wrong:** Importing from `react-router-dom` or using Vite plugin for SSR — wrong mode for our SPA.
**Why it happens:** React Router v7 documentation defaults to "framework mode" which requires a build server. Our app is a client-side SPA.
**How to avoid:** Import from `'react-router'` (not `'react-router-dom'`). Use `<BrowserRouter>` and `<Routes>` for library mode. Don't use Vite plugin for React Router.
**Warning signs:** Import errors from `react-router-dom`, SSR-related build failures.

### Pitfall 6: Vite Proxy Not Working in Docker
**What goes wrong:** Vite dev server proxy works locally but not in Docker.
**Why it happens:** Docker Compose service names (`backend`) don't resolve from the Vite dev server container. In Docker, the proxy target needs to be `http://backend:8000` (Docker network), while locally it's `http://localhost:8000`.
**How to avoid:** Use environment variable `VITE_API_BASE` for production. For Docker dev, set proxy target to `http://backend:8000`. For local dev, use `http://localhost:8000`. The Dockerfile should build static files (no proxy needed in production).
**Warning signs:** 502 errors or CORS errors only in Docker.

### Pitfall 7: Over-fetching on Line Slider Changes
**What goes wrong:** Every 0.5 increment slider change triggers a full `/api/players/{id}/hitrates?stat=pts&line=24.5` fetch, hammering the API.
**Why it happens:** React re-renders on every slider value change. Without debouncing, 10 slider drags = 10 fetches.
**How to avoid:** Debounce the slider value (300ms) before fetching hit rates. Use a local state for the slider position and a debounced effect for the fetch. Or, compute adjusted hit rates client-side if the backend supports it (currently it does via the `stat` + `line` params on `/hitrates`).
**Warning signs:** Network tab shows rapid sequential requests when dragging the slider.

## Code Examples

Verified patterns from official sources:

### Vite Config with React + Tailwind + Proxy
```javascript
// vite.config.js
// Source: [CITED: vitejs/vite docs — server.proxy config]
// Source: [CITED: tailwindcss.com/docs/installation — Vite plugin setup]
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### React 19 Entry Point
```jsx
// src/main.jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

### Tailwind v4 CSS with Dark Mode Customization
```css
/* src/index.css */
/* Source: [CITED: tailwindcss.com/docs/dark-mode — @custom-variant] */
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --color-bg-primary: #0f172a;
  --color-bg-card: #1e293b;
  --color-bg-card-hover: #334155;
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
  --color-border: #334155;
  --color-prob-high: #22c55e;
  --color-prob-moderate: #eab308;
  --color-prob-low: #ef4444;
}
```

### Probability Badge Component
```jsx
// src/components/ProbabilityBadge.jsx
// Based on D-07: large color-coded percentage badge
function getProbabilityColor(probability) {
  if (probability >= 0.65) return 'bg-prob-high text-white';
  if (probability >= 0.45) return 'bg-prob-moderate text-black';
  return 'bg-prob-low text-white';
}

export default function ProbabilityBadge({ probability }) {
  const pct = Math.round(probability * 100);
  return (
    <div
      className={`inline-flex items-center justify-center rounded-lg px-3 py-1.5 
        text-2xl font-bold ${getProbabilityColor(probability)}`}
    >
      {pct}%
    </div>
  );
}
```

### Alert Badge Component
```jsx
// src/components/AlertBadge.jsx
// Based on D-12: colored badges for injury/news alerts
const ALERT_STYLES = {
  OUT: 'bg-red-600 text-white',
  QUESTIONABLE: 'bg-yellow-500 text-black',
  INJURY: 'bg-orange-500 text-white',
  PROBABLE: 'bg-green-500 text-white',
  TRADE: 'bg-blue-500 text-white',
  SUSPENSION: 'bg-red-800 text-white',
  G_LEAGUE: 'bg-gray-500 text-white',
  REST: 'bg-gray-400 text-black',
};

export default function AlertBadge({ alert }) {
  const style = ALERT_STYLES[alert.alert_type] || 'bg-gray-400 text-black';
  
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}
      title={`${alert.subcategory || alert.alert_type}: ${alert.headline}`}
    >
      {alert.alert_type}
    </span>
  );
}
```

### API Client Module
```javascript
// src/api/client.js
const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function fetchJSON(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Named API calls
export const api = {
  searchPlayers: (query) => fetchJSON(`/api/players?search=${encodeURIComponent(query)}`),
  getPlayer: (id) => fetchJSON(`/api/players/${id}`),
  getPlayerProps: (id) => fetchJSON(`/api/players/${id}/props`),
  getPlayerGameLogs: (id, limit = 50) => fetchJSON(`/api/players/${id}/gamelogs?limit=${limit}`),
  getPlayerHitRates: (id, stat, line) => fetchJSON(`/api/players/${id}/hitrates?stat=${stat}&line=${line}`),
  getPlayerLines: (id) => fetchJSON(`/api/players/${id}/lines`),
  getPlayerNews: (id) => fetchJSON(`/api/players/${id}/news`),
  getTeams: () => fetchJSON('/api/teams'),
  healthCheck: () => fetchJSON('/api/health'),
};
```

### Docker Configuration Updates
```dockerfile
# hoopprophet/Dockerfile (updated for Vite)
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve@latest
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

```yaml
# docker-compose.yml (updated frontend service)
# The VITE_API_BASE is baked into the build at build time for production.
# In dev, Vite proxy handles /api/* routing.
frontend:
  build:
    context: ./hoopprophet
    args:
      - VITE_API_BASE=http://backend:8000
  ports:
    - "3000:3000"
  depends_on:
    - backend
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CRA (react-scripts) | Vite 8.x | CRA effectively deprecated ~2023, Vite is the standard in 2025-26 | Faster builds (10-100x), native ESM, no webpack config needed |
| MUI component library | Tailwind CSS v4 utility classes | Tailwind v4 released early 2025, CSS-first config | Dark-mode native, smaller bundle, no component library overhead |
| Visx v3 (React 18 only) | Visx v4 alpha (React 19 support) | Alpha released 2024, still alpha as of 2026-04 | Must use @next tag; stable v4 not yet released |
| React Router v6 (`react-router-dom`) | React Router v7 (`react-router`) | v7 released 2024-2025 | Single package, framework + library modes; SPA uses library mode |
| Tailwind CSS v3 (config file) | Tailwind CSS v4 (CSS-first `@theme`) | v4 released Jan 2025 | No `tailwind.config.js`, all config in CSS via `@import "tailwindcss"` and `@theme` |
| `process.env.REACT_APP_*` | `import.meta.env.VITE_*` | CRA → Vite migration standard | Different env var prefix, module-level access |

**Deprecated/outdated:**
- **react-scripts (CRA):** Officially in maintenance mode. No new features. Replace with Vite.
- **@mui/material (MUI):** Removed per D-04. Heavy bundle (~80KB gzipped just for core). Tailwind + custom components are lighter and more flexible for dark dashboard.
- **framer-motion:** Removed per D-04 (V1 dependency). Use CSS transitions and Tailwind `animate-` utilities for D-09 micro-transitions.
- **react-router-dom:** React Router v7 uses single `react-router` package. `react-router-dom` is the v6 import path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Visx v4 alpha (@next) is stable enough for production hit rate bar charts | Standard Stack | Alpha packages may have breaking changes or bugs. Mitigation: pin exact alpha version, test thoroughly. |
| A2 | react-hot-toast is the best toast library choice (5KB, simple API) | Standard Stack | Could use react-toastify instead if more features needed, but adds bundle weight. |
| A3 | Tailwind v4 @theme custom colors will cover the design token needs (probability colors, background shades) | Architecture Patterns | If design tokens become highly dynamic or require runtime theming, CSS variables via @theme may not be sufficient. But dark-mode-only with static tokens is well within Tailwind v4's capability. |
| A4 | The backend API responses documented in Phase 5/6 contexts are accurate and stable | Code Examples | If API shapes changed since phases 5/6 were built, fetch hooks will need adjustment. Verify with actual API calls during implementation. |
| A5 | Half-point line slider can use a native range input styled with Tailwind | Code Examples | Custom slider with 0.5 increments may need a custom component if native range doesn't provide sufficient visual feedback. Tailwind can style the track/thumb, but 0.5 step increments require `step="0.5"` attribute. |

**If empty:** N/A — assumptions documented above.

## Open Questions

1. **Visx v4 Alpha Stability**
   - What we know: Visx v4 alpha (4.0.0-alpha.11) has React 19 peer dependency. Airbnb's README confirms work is in progress.
   - What's unclear: Whether v4 will reach stable before this phase completes. Alpha packages can have breaking changes.
   - Recommendation: Pin exact alpha version in package.json. If critical bugs arise, Recharts is the fallback (higher-level but larger bundle).

2. **Backtest Calibration Chart Library Choice**
   - What we know: D-17 requires a calibration chart (predicted vs observed hit rates). This is a line/area chart, not a bar chart.
   - What's unclear: Whether Visx's `@visx/shape` (AreaClosed, LinePath) is sufficient or if we need a higher-level charting API.
   - Recommendation: Use Visx `AreaClosed` and `LinePath` from `@visx/shape` for the calibration chart. Same package family, consistent with hit rate charts. No additional library needed.

3. **API Base URL in Docker Production**
   - What we know: V1 uses `REACT_APP_API_BASE` (CRA). V2 uses `VITE_API_BASE` (Vite). Vite bakes env vars at build time, not runtime.
   - What's unclear: Whether the Docker deployment needs runtime-configurable API URL or if build-time is sufficient.
   - Recommendation: Build-time `VITE_API_BASE` with default empty string (Vite proxy handles `/api` in dev). For production Docker, pass `VITE_API_BASE=http://backend:8000` as build arg. The static build doesn't need a proxy since the frontend is served separately.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Build toolchain, dev server | ✓ | 24.14.0 | — |
| npm | Package management | ✓ | 11.9.0 | — |
| npx | Package runners, scaffolding | ✓ | 11.9.0 | — |
| Vite | Build + HMR | ✗ (install) | 8.0.9 (latest) | — |
| Python 3.11 | Backend API (for integration testing) | ✓ (Docker) | 3.11-slim | — |
| Docker | Containerized deployment | ✓ (Docker Desktop assumed) | — | — |

**Missing dependencies with no fallback:**
- Vite, Tailwind, React Router, Visx — all need `npm install`. This is expected for a frontend rebuild.

**Missing dependencies with fallback:**
- None identified. All frontend dependencies are npm packages.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.2.x |
| Config file | `vitest.config.js` (to be created in Wave 0) |
| Quick run command | `npx vitest run --reporter=verbose` |
| Full suite command | `npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Component architecture renders correctly | unit | `npx vitest run src/components/` | ❌ Wave 0 |
| UI-02 | Search autocomplete fetches and displays players | integration | `npx vitest run src/components/PlayerSearch.test.jsx` | ❌ Wave 0 |
| UI-03 | Prop card renders probability badge and hit rate chart | unit | `npx vitest run src/components/PropCard.test.jsx` | ❌ Wave 0 |
| UI-04 | Game log table renders rows from API data | unit | `npx vitest run src/components/GameLogTable.test.jsx` | ❌ Wave 0 |
| UI-05 | Alert badges render with correct colors per type | unit | `npx vitest run src/components/AlertBadge.test.jsx` | ❌ Wave 0 |
| UI-06 | Backtest page renders summary stats | unit | `npx vitest run src/pages/BacktestPage.test.jsx` | ❌ Wave 0 |
| UI-07 | Dark theme renders correctly | integration | manual + visual check | ❌ Wave 0 |
| UI-08 | Hit rate charts render L5/L10/L20/Season bars | unit | `npx vitest run src/components/HitRateChart.test.jsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run --reporter=verbose`
- **Per wave merge:** `npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `vitest.config.js` — Vitest configuration with jsdom environment
- [ ] `src/setupTests.js` — @testing-library/jest-dom setup
- [ ] All test files listed above — Wave 0 must create test infrastructure
- [ ] Framework install: `npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event`
- [ ] `package.json` scripts: add `"test": "vitest run"`, `"test:watch": "vitest"`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No user auth (out of scope per PROJECT.md) |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No protected resources |
| V5 Input Validation | yes | Zod or manual validation for player ID params, search query sanitization |
| V6 Cryptography | no | No crypto needed in frontend |
| V8 Data Protection | partial | API responses may contain player data — no PII concerns for public NBA data |
| V10 Error Handling | yes | Toast notifications for API errors (no stack traces in UI), fetch wrapper catches network errors |
| V14 Config | yes | VITE_API_BASE env var, no secrets in frontend code |

### Known Threat Patterns for React SPA + API

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via player name injection | Tampering | React auto-escapes JSX. Don't use `dangerouslySetInnerHTML` for player names. |
| CSRF on API calls | Tampering | API uses JSON responses, no form submissions. CORS configured on backend. |
| Sensitive data in localStorage | Info disclosure | Don't store sensitive data in localStorage. No auth tokens needed. |
| Supply chain attack via npm dependencies | Tampering | Pin exact versions in package.json. Run `npm audit` during CI. |
| API endpoint exposure | Info disclosure | Backend CORS only allows localhost:3000 and frontend:3000 (already configured). |

## Sources

### Primary (HIGH confidence)
- Context7 `/vitejs/vite` — Vite server proxy config, React plugin setup
- Context7 `/remix-run/react-router` — React Router v7 createBrowserRouter, library mode routing
- Context7 `/airbnb/visx` — Bar charts, ParentSize responsive, ScaleSVG, Group, gradient patterns
- npm registry — Version verification for all packages (React 19.1.0, Vite 8.0.9, Tailwind 4.2.4, React Router 7.14.2, Visx 4.0.0-alpha.11)
- tailwindcss.com/docs/installation — Vite plugin setup, CSS-first configuration
- tailwindcss.com/docs/dark-mode — `@custom-variant` for class-based dark mode

### Secondary (MEDIUM confidence)
- GitHub airbnb/visx — README with v4 alpha React 19 support announcement, package structure
- HoopProphet codebase — server/api/players.py, server/api/news.py, server/services/ for actual API shapes
- HoopProphet CONTEXT.md — Phase 5/6 locked decisions on API response format

### Tertiary (LOW confidence)
- react-hot-toast bundle size claim (5KB) — from training knowledge, not directly verified in this session
- Calibration chart pattern using Visx AreaClosed — assumed from Visx docs, not tested in this session

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all versions verified via npm registry, Tailwind/Vite docs confirmed
- Architecture: HIGH — patterns well-established for React SPA + Tailwind dark dashboard + Visx charts
- Pitfalls: HIGH — Visx v3/v4 React 19 incompatibility confirmed via npm peer deps check; CRA→Vite migration well-documented

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days — stable for stack, shorter for Visx v4 alpha which may change)