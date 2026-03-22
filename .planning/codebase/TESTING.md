# Testing Patterns

**Analysis Date:** 2026-03-22

## Test Framework

**Runner:**
- **Jest** (bundled with Create React App via `react-scripts` 5.0.1). No standalone `jest.config.js`—configuration comes from `react-scripts`.
- Config: embedded in CRA; see `hoopprophet/package.json` `eslintConfig.extends` including `react-app/jest` for ESLint + Jest integration.

**Assertion Library:**
- **Jest** matchers, plus **@testing-library/jest-dom** for DOM assertions (declared in `hoopprophet/package.json` dependencies).

**React testing:**
- **@testing-library/react** and **@testing-library/user-event** are listed in `hoopprophet/package.json`.

**Run Commands:**
```bash
cd hoopprophet && npm test              # Interactive Jest via react-scripts (watch mode by default)
cd hoopprophet && CI=true npm test      # Single run (typical for CI)
cd hoopprophet && npm test -- --coverage  # Coverage report (Jest flag passthrough)
```

**Backend:**
- **Not detected:** `server/requirements.txt` contains no `pytest`, `httpx`, `pytest-asyncio`, or `unittest` extensions. No `tests/` tree or `test_*.py` files found in the explored layout.

## Test File Organization

**Location:**
- **No test files present.** `hoopprophet/src/` contains only `App.js`, `index.js`, and `assets/`—no `*.test.js`, `*.spec.js`, or `setupTests.js`.
- Default CRA samples (`App.test.js`, `setupTests.js`) are absent.

**Naming:**
- When adding tests, follow CRA convention: colocate `ComponentName.test.js` next to `ComponentName.js` or use `__tests__/` under `src/` (CRA supports both).

**Structure:**
```
hoopprophet/src/
├── App.js          # no App.test.js yet
├── index.js
└── assets/
```

## Test Structure

**Suite Organization:**
- Not applicable—no tests. Recommended pattern for new work:

```javascript
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders headline', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /hoopprophet/i })).toBeInTheDocument();
  });
});
```

**Patterns:**
- Add `src/setupTests.js` if importing `@testing-library/jest-dom` globally (CRA auto-imports when file exists).

## Mocking

**Framework:** Jest (`jest.fn()`, `jest.mock()`).

**Patterns:**
- **fetch:** Use `global.fetch = jest.fn()` or `jest.spyOn(global, 'fetch')` and resolve with `Response` mocks when testing `hoopprophet/src/App.js` data loading.
- **Environment:** Use `process.env.REACT_APP_API_BASE` in tests or mock `fetch` so tests do not hit `http://localhost:8000`.

**What to Mock:**
- Network: all `fetch` calls to `${API_BASE}/players`, `/teams`, `/predict`.
- Optional: `framer-motion` if animations complicate assertions (`jest.mock('framer-motion', () => ({ motion: { div: 'div' } }))` pattern is common).

**What NOT to Mock:**
- React itself; prefer Testing Library queries over implementation details.

## Fixtures and Factories

**Test Data:**
- No shared fixtures. For API tests, build minimal JSON matching backend shapes from `server/app.py` (e.g. `{ full_name, id }` for players).

**Location:**
- Place under `hoopprophet/src/__fixtures__/` or next to tests when introduced.

## Coverage

**Requirements:** None enforced in repo (no CI config detected; no coverage thresholds in `package.json`).

**Ignored output:** `hoopprophet/.gitignore` includes `/coverage`.

**View Coverage:**
```bash
cd hoopprophet && npm test -- --coverage --watchAll=false
```

## Test Types

**Unit Tests:**
- **Frontend:** Not yet written; natural units include `prettifyStatName`, filter logic inside `Autocomplete` `filterOptions`, and `handlePredict` error branches (extract functions first if testing in isolation).
- **Backend:** Add with `pytest` + `TestClient` from `fastapi.testclient` for `server/app.py` routes; mock `nba_api` and `ml` layers to avoid live network and heavy ML in unit tests.

**Integration Tests:**
- Not present. Future: Docker Compose or local stack tests hitting `/health`, `/players`, `/teams` with mocked external APIs.

**E2E Tests:**
- Not used (no Playwright/Cypress in `hoopprophet/package.json`).

## Common Patterns

**Async Testing:**
```javascript
await waitFor(() => {
  expect(screen.getByText(/prediction complete/i)).toBeInTheDocument();
});
```

**Error Testing:**
```javascript
global.fetch = jest.fn(() => Promise.reject(new Error('network')));
render(<App />);
await waitFor(() => {
  expect(screen.getByText(/advanced basketball analytics/i)).toBeInTheDocument();
});
```

**FastAPI (recommended when adding backend tests):**
```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
```

---

*Testing analysis: 2026-03-22*
