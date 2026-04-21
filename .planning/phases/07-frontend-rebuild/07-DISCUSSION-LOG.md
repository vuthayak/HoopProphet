# Phase 7: Frontend Rebuild - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-21
**Phase:** 07-frontend-rebuild
**Mode:** discuss
**Areas discussed:** Architecture & Routing, Visual Style & Layout, Page Structure & Data Flow, Build & Migration, V1 Migration Strategy

## Architecture & Routing

| # | Question | Options Presented | Selection |
|---|----------|--------------------|----------|
| 1 | How should users navigate between views? | Client-side SPA routing (Recommended), No routing (state-based) | Client-side SPA routing (React Router) |
| 2 | How should the frontend manage state and API calls? | Local state + fetch per page (Recommended), React Query, Zustand/Redux | Local state + fetch per page |
| 3 | How should components be organized? | Feature-based folders (Recommended), Category-based folders | Feature-based folders (page/components) |
| 4 | How should the rebuild handle component styling? | Custom design system with Tailwind (Recommended), MUI + deep theme override, Tailwind-only no component lib | Custom design system with Tailwind — user noted "use the ui-ux-pro-max skill to create a design system better catered towards this type of project/app" |
| 5 | Theme mode? | Dark mode only (Recommended), Light + dark toggle | Dark mode only |
| 6 | Charting library for hit rate bars and probability visualizations? | Recharts (Recommended), Visx (Airbnb), Nivo | Visx (Airbnb) |

## Visual Style & Layout

| # | Question | Options Presented | Selection |
|---|----------|--------------------|----------|
| 7 | How should hit rate visualization appear on the player page? | Inline horizontal bars per prop (Recommended), Separate chart section per card, Tabular grid with mini bars | Separate chart section per card |
| 8 | How should ML-predicted probability be displayed on each prop card? | Large color-coded percentage badge (Recommended), Thin progress bar under prop name | Large color-coded percentage badge |
| 9 | How should adjustable stat lines work? | Half-point slider per prop card (Recommended), +/- buttons for 0.5 steps, Edit mode toggle for all lines | Half-point slider per prop card |
| 10 | What color scheme direction for the dark-mode dashboard? | Blue-purple dark (Recommended), Neutral dark with accents, Dark with basketball accents | Delegated to design skill — user said "use the ui-ux-pro-max skill to figure this out" |
| 11 | How should the UI handle transitions and loading? | Polished micro-transitions (Recommended), Minimal animations | Polished micro-transitions (framer-motion still available) |
| 12 | What shows on first load before a player is selected? | Simple message + prominent search (Recommended), Pre-populated with popular picks | Simple message + prominent search |
| 13 | How dense should prop cards be on the player page? | One card stacked mobile-first, Compact grid 2-3 per row desktop-first (Recommended), Responsive grid 1/2/3 columns | Compact grid, 2-3 per row (desktop-first) |
| 14 | How should recent game logs appear on the player page? | Compact scrollable table below props (Recommended), Expandable section hidden by default, Separate scroll section | Compact scrollable table below props |
| 15 | How should injury/news flags appear on the player page? | Badge next to player name with hover details (Recommended), Alert banner at top of page | Badge next to player name with hover details |

## Page Structure & Data Flow

| # | Question | Options Presented | Selection |
|---|----------|--------------------|----------|
| 16 | What pages should the app have? | 3 pages Home/Player/Backtest (Recommended), 2 pages Home+Player/Backtest, 4+ pages incl Daily Picks | 3 pages: Home, Player, Backtest |
| 17 | How should the player page organize its content? | Single scroll page (Recommended), Tabbed sections (Overview/Logs/News), Split layout sidebar | Tabbed sections (Overview/Logs/News) |
| 18 | Where should player search live? | Persistent top navbar with search (Recommended), Home hero search + minimal header | Persistent top navbar with search |
| 19 | When should API data be fetched? | On-demand per page load parallel (Recommended), Prefetch player/team lists, Eager load all | On-demand per page load, parallel |
| 20 | What should the back-test page show? | Stats dashboard summary/season table/calibration (Recommended), Minimal calibration + key numbers | Stats dashboard: summary → season table → calibration chart |
| 21 | How should loading and error states look? | Skeleton placeholders + toast errors (Recommended), Spinner + inline errors, No loading UI | Skeleton placeholders + toast errors |

## Build & Migration

| # | Question | Options Presented | Selection |
|---|----------|--------------------|----------|
| 22 | How should we handle the V1 transition? | Clean rebuild from scratch (Recommended), Parallel build switch when ready, Incremental refactor | Clean rebuild from scratch |
| 23 | Build tooling: CRA vs Vite? | Migrate to Vite (Recommended), Stay with CRA | Migrate to Vite |
| 24 | Responsive design approach? | Desktop-first responsive down (Recommended), Mobile-first scale up, Desktop only for now | Desktop-first, responsive down |
| 25 | Frontend testing strategy? | RTL component tests only (Recommended), RTL + Playwright E2E, No automated tests | RTL component tests only |

## Discussion Notes

- User explicitly referenced using a design skill (ui-ux-pro-max) for color palette and visual design system decisions — these should be delegated during planning/implementation, not hard-coded in context.
- User chose Visx over the recommended Recharts — Visx provides more customization for data-dense betting dashboard visuals.
- Tabbed player page was chosen over single-scroll because it cleanly separates props analysis from reference data (game logs) and alerts (news).
- Separating hit rate charts into their own section per prop card (rather than inline bars) gives L5/L10/L20/Season comparison more room and readability.