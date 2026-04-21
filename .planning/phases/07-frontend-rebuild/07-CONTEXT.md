# Phase 7: Frontend Rebuild - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Component-based React app replacing V1's monolithic 590-line App.js. Delivers player analysis (prop cards with ML probability, hit rate visualization, adjustable lines), back-test display (model accuracy and calibration), and player search with autocomplete. Consumes Phase 5/6 API endpoints. Daily picks dashboard is out of scope (v2 requirement).

</domain>

<decisions>
## Implementation Decisions

### Architecture & Routing
- **D-01:** Client-side SPA routing with React Router — / (home/search), /player/:id (player analysis), /backtest (model accuracy). Shareable URLs, browser back/forward works.
- **D-02:** Local state management (useState/useEffect) with fetch calls per page component. No external state library — single player at a time, no global state needed beyond player list.
- **D-03:** Feature-based folder structure: `pages/` for route-level components, `components/` for reusable UI (PropCard, HitRateChart, GameLogTable, PlayerSearch, AlertBadge). Grouped by feature, not type.
- **D-04:** MUI is removed entirely. Custom design system built with Tailwind CSS — dark-mode native, compact cards, probability color coding, data-dashboard aesthetics. Design details (color palette, spacing, typography) delegated to design skill during planning/implementation.

### Visual Style & Layout
- **D-05:** Dark mode only. No light theme toggle. Background, text, and data elements optimized for dark readability.
- **D-06:** Hit rate visualization as a separate chart section per prop card — not inline bars. Each prop card has its own Visx bar chart showing L5/L10/L20/Season hit rates.
- **D-07:** ML-predicted probability displayed as a large color-coded percentage badge (green=high, yellow=moderate, red=low). Primary decision signal for bettors — visible at a glance.
- **D-08:** Adjustable stat lines via half-point slider per prop card. User drags to adjust line (0.5 increments), hit rates update. Natural for bettors who think in half-points.
- **D-09:** Polished micro-transitions for page loads and data refreshes. Prop cards fade/slide in, charts animate on mount. Not flashy — just polished.
- **D-10:** Compact grid layout for prop cards: 2-3 per row on desktop, 1 per row on mobile. Desktop-first with responsive breakpoints down.
- **D-11:** Game log table displayed as a compact scrollable table below prop cards on the player page. Data density prioritized over visual flourish.
- **D-12:** Injury/news alerts displayed as colored badges next to player name (red=OUT, yellow=QUESTIONABLE, orange=INJURY). Hover for details. Immediate visibility without taking space.

### Page Structure & Data Flow
- **D-13:** Three pages: Home (search landing), Player (tabs: Overview/Game Logs/News), Backtest (model accuracy dashboard).
- **D-14:** Player page uses tabbed layout: Overview tab (prop cards + lines), Game Logs tab, News tab. Cleaner separation than single scroll page.
- **D-15:** Persistent top navbar with logo, autocomplete search input (always visible), and nav links (Backtest, Home). Search is primary action, always accessible.
- **D-16:** Data fetched on-demand per page load. Props, game logs, and alerts fetched in parallel (Promise.all). Hit rates refetch only when lines are adjusted. No app-level prefetching.
- **D-17:** Backtest page displays: summary stats at top (overall accuracy, Brier score, ROI) → season-by-season breakdown table → calibration chart (predicted vs observed). Read-only dashboard, no interactivity needed.
- **D-18:** Simple message on home/landing page before player is selected: "Search for a player to get started" with prominent search input. No illustrations or pre-populated content.
- **D-19:** Skeleton placeholders (gray pulsing shapes) for loading states. Toast notifications for errors. Clean data-arrival feel.

### Build & Migration
- **D-20:** Clean rebuild from scratch. Delete all V1 frontend code (hoopprophet/src/) and build new component structure. V1 code is 590 lines of monolithic JSX with no reusable components — no point refactoring.
- **D-21:** Migrate from CRA (react-scripts) to Vite. CRA is effectively deprecated. Vite provides faster builds, better HMR, and smaller bundles. Rebuilding anyway — no reason to stay on CRA.
- **D-22:** Desktop-first responsive design with breakpoints down to tablet and mobile. Desktop is primary (bettors analyzing data), mobile is usable but not optimized. Min 3 breakpoints: desktop (>1024px), tablet (768-1024px), mobile (<768px).
- **D-23:** React Testing Library for component tests. Match what's already in package.json deps. Focus on rendering and interaction testing, not visual regression.

### the agent's Discretion
- Exact Tailwind design tokens (colors, spacing, typography) — delegated to design skill
- Visx chart styling details (axis formatting, bar colors, animation timing)
- Skeleton placeholder shapes and timing
- Toast notification library choice (react-hot-toast, react-toastify, or custom)
- Router guard/hook patterns for data loading
- Exact responsive breakpoint values
- Component internal state patterns

### Folded Todos
(No pending todos were folded into scope.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — UI-01 (component architecture), UI-02 (autocomplete search), UI-03 (prop cards with hit rate charts, ML probability, adjustable lines), UI-04 (game log table), UI-05 (news/injury flags on player page), UI-06 (back-test page), UI-07 (clean modern data-focused design), UI-08 (bar charts for hit rates). Also PROP-03 (adjustable lines), PROP-02 (default lines), NEWS-03 (news flags on player page).
- `.planning/ROADMAP.md` — Phase 7 goal, success criteria, and requirements mapping
- `.planning/PROJECT.md` — Key decisions: data-backed prop picks, no Gemini summaries, web-first, no mobile app, no user accounts

### API endpoints (Phase 5-6 outputs — frontend consumes these)
- `server/api/players.py` — Player endpoints: `/api/players`, `/api/players/{id}`, `/api/players/{id}/props`, `/api/players/{id}/gamelogs`, `/api/players/{id}/hitrates`, `/api/players/{id}/lines`
- `server/api/news.py` — News endpoint: `/api/players/{id}/news`
- `server/api/teams.py` — Team endpoint: `/api/teams`
- `server/app.py` — FastAPI app structure, CORS middleware, lifespan, `/api/health`

### Prior phase contexts (locked decisions)
- `.planning/phases/05-api-layer-prop-serving/05-CONTEXT.md` — Flat /api routes, lean JSON, 1% probability rounding, graceful degradation, hit rate sample counts, top 5 props by probability
- `.planning/phases/06-news-injury-flags/06-CONTEXT.md` — Alert badges (INJURY, OUT, QUESTIONABLE, etc.), embedded alerts in player response, `/api/players/{id}/news` for full details, 6h TTL cache

### Existing frontend (to replace, not extend)
- `hoopprophet/src/App.js` — V1 monolithic 590-line React component (MUI + framer-motion)
- `hoopprophet/package.json` — React 19, MUI 7.2, framer-motion, CRA react-scripts 5.0

### Codebase conventions
- `.planning/codebase/CONVENTIONS.md` — Naming patterns, code style, error handling patterns
- `.planning/codebase/STRUCTURE.md` — Project layout, where to add new code, entry points
- `.planning/codebase/STACK.md` — Current tech stack analysis
- `.planning/codebase/ARCHITECTURE.md` — Data flow, API patterns, state management

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/api/players.py` — Player router with all V2 endpoints the frontend will consume: search, detail, props, game logs, hit rates, lines
- `server/api/news.py` — News router for player alert data
- `server/api/teams.py` — Teams router for team info
- `server/services/player_service.py` — PlayerService with search and data access (already returns lean JSON)
- `server/services/prediction_service.py` — PredictionService for props and lines
- `server/services/hitrate_service.py` — HitRateService for L5/L10/L20/season hit rate computation
- `server/core/config.py` — Centralized config (DB_PATH, DATA_DIR, MODEL_ARTIFACT_PATH)
- `hoopprophet/src/App.js` — V1 code to study for API call patterns and data shapes (but NOT to extend or refactor)

### Established Patterns
- FastAPI backend serves lean JSON from SQLite cache — no live NBA API calls per request (Phase 5 decision)
- `/api` flat prefix, resource-based routes (Phase 5 decision D-15)
- CORS allows localhost:3000 and frontend:3000 (Phase 5/6)
- V1 uses `REACT_APP_API_BASE` env var (defaults to `http://localhost:8000`, `http://backend:8000` in Docker)
- Hit rates include sample counts alongside rates per D-09 in Phase 5 context
- Probabilities rounded to 1% (D-08) — frontend should not over-precision these
- Model artifact loaded at FastAPI lifespan startup — `/health` endpoint returns `model_loaded` status

### Integration Points
- Frontend fetches from all Phase 5/6 API endpoints defined in `server/api/players.py` and `server/api/news.py`
- Vite dev server proxies API calls to backend (replace CRA proxy config)
- Docker Compose runs frontend (Vite build) + backend (uvicorn) — update `hoopprophet/Dockerfile` and `docker-compose.yml`
- NBA CDN for player headshots (`https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png`) and team logos — used in V1, keep in V2

</code_context>

<specifics>
## Specific Ideas

- Prop cards should feel like betting analytics — compact, data-dense, probability-first. Not a generic dashboard.
- Color-coded probability badges: bettors see green/yellow/red and instantly know which props are worth taking
- Half-point slider is the natural interaction for sports bettors — lines are always in 0.5 increments
- Separate chart section per prop card gives hit rate bars room to breathe — L5/L10/L20/Season comparison is the key insight
- Tab layout on player page separates concerns: props analysis vs game history vs news alerts
- V1's design used MUI defaults with light green background — V2 should feel professional, dark, data-focused
- Game log table is reference data — important but secondary to prop analysis

</specifics>

<deferred>
## Deferred Ideas

- Daily picks dashboard — PICK-01/PICK-02/PICK-03 are v2 requirements, out of scope per PROJECT.md
- League-wide leaderboard or comparison views — future consideration
- User accounts / authentication — explicitly out of scope per PROJECT.md
- Mobile app or PWA — web-first per PROJECT.md, mobile deferred
- Light theme toggle — dark-mode only for V2
- Push notifications for news alerts — API-only in Phase 6, not a frontend feature yet
- Sportsbook odds comparison — v2 requirement (ODDS-01/02/03), out of scope

</deferred>

---

*Phase: 07-frontend-rebuild*
*Context gathered: 2026-04-21*