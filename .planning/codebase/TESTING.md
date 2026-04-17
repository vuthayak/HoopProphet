# Testing Patterns

**Analysis Date:** 2026-04-17

## Test Framework

**Backend Runner:**
- pytest >=8.0.0 with pytest-timeout >=2.2.0
- Config: `pyproject.toml` (minimal):
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["server/tests"]
  timeout = 30
  ```

**Frontend:**
- react-scripts 5.0.1 (includes Jest + React Testing Library)
- `@testing-library/react` 16.3.0
- `@testing-library/jest-dom` 6.6.4
- `@testing-library/user-event` 13.5.0
- **No frontend test files exist** — only boilerplate from CRA

## Run Commands

```bash
# Backend — from project root
cd /path/to/project
pytest                              # Run all backend tests
pytest server/tests/test_db.py     # Run single test file
pytest server/tests/ -v             # Verbose output
pytest server/tests/ --timeout=30   # With timeout (already in config)

# Frontend — from hoopprophet/ directory
cd hoopprophet
npm test                            # Run React tests (none exist yet)
```

**Coverage:** No coverage tooling configured. No coverage targets enforced.

## Test File Organization

**Location:** Tests are in a separate `server/tests/` directory (not co-located with source).

**Naming:** `test_` prefix with `snake_case` matching the module under test:
```
server/tests/
├── __init__.py
├── conftest.py                      # Shared fixtures
├── test_nba_client.py               # Tests for server/pipeline/nba_client.py
├── test_ingest.py                   # Tests for server/pipeline/ingest.py
├── test_db.py                       # Tests for server/pipeline/db/ module
├── test_feature_pipeline.py         # Tests for server/pipeline/features.py
├── test_rolling_features.py         # Tests for server/pipeline/processors/rolling_features.py
├── test_contextual_features.py      # Tests for server/pipeline/processors/contextual_features.py
├── test_dnp_synthesis.py            # Tests for server/pipeline/processors/dnp_synthesis.py
```

**Import convention:** Import from package path:
```python
from server.pipeline.nba_client import NBAClient
from server.pipeline.db.queries import get_remaining_work
from server.pipeline.feature_config import PRIMARY_STATS
```

## Test Structure

**Suite Organization:**

Two styles are used:

1. **Standalone functions** (most common):
```python
def test_rolling_averages_columns_exist(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))
    for stat in PRIMARY_STATS:
        for window in WINDOWS_PRIMARY:
            assert f"{stat}_avg_L{window}" in result.columns
```

2. **Class-based grouping** (used in `test_ingest.py` and `test_dnp_synthesis.py`):
```python
class TestGameLogsStored:
    def test_gamelogs_stored(self, tmp_db):
        ...

class TestDNPSynthesis:
    def test_dnp_rows_created(self, tmp_db):
        ...
    def test_no_false_dnp_for_traded_player(self, tmp_db):
        ...
    def test_dnp_idempotent(self, tmp_db):
        ...
```

**Assertion style:** Plain `assert` statements, not `self.assertEqual()`:
```python
assert count > 0
assert result["rows"] > 0
assert jokic.loc[5, "pts_avg_L5"] == pytest.approx(expected)
```

When comparing floats, use `pytest.approx()`:
```python
assert bos[0] == pytest.approx(108.5)
```

## Fixtures and Test Data

**conftest.py** provides three core fixtures:

1. **`tmp_db`** — Fresh SQLite database with schema:
```python
@pytest.fixture
def tmp_db():
    """Provide a temporary SQLite database with all tables created."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = get_connection(db_path)
    init_db(conn)
    yield conn
    conn.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

2. **`sample_game_log_df`** — DataFrame with 5 realistic game log rows for Jokic (player_id 203999).

3. **`feature_db`** — Pre-loaded database with two players (LeBron and Jokic), two teams, team stats for 2 seasons, and ~25 game logs including DNP rows. This is the most important fixture for feature pipeline tests.

**Helper functions** (module-scoped, not fixtures):
```python
def _make_client():
    """Create an NBAClient with a disposable temp cache."""
    ...

def _create_mock_client():
    """Build a MagicMock NBAClient with realistic return values."""
    ...

def _seed_player(conn, player_id=203999):
    """Insert a player so FK constraints are satisfied."""
    ...
```

## Mocking

**Framework:** `unittest.mock` (stdlib) — no additional mocking libraries.

**Pattern for NBA API mocking (unit tests):**
```python
from unittest.mock import MagicMock, patch

def test_retry_on_connection_error():
    client = _make_client()
    mock_instance = MagicMock()
    mock_instance.get_data_frames.return_value = [sample_df]

    with patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog", side_effect=side_effect):
        result = client.fetch_player_gamelog(203999, "2023-24")
```

**Pattern for full client mocking (integration tests):**
```python
def _create_mock_client():
    client = MagicMock()
    client.get_all_teams.return_value = [...]
    client.fetch_player_gamelog.side_effect = _mock_gamelog
    return client
```

**Pattern for system-level mocking:**
```python
class TestFullPipelineMock:
    @patch("server.pipeline.ingest.get_connection")
    @patch("server.pipeline.ingest.NBAClient")
    def test_full_pipeline_mock(self, mock_client_cls, mock_get_conn, tmp_db):
        mock_client = _create_mock_client()
        mock_client_cls.return_value = mock_client
        wrapper = MagicMock(wraps=tmp_db)
        wrapper.close = MagicMock()
        mock_get_conn.return_value = wrapper
```

**What to Mock:**
- External API calls (`nba_api` endpoints)
- Database connections (wrap real temp SQLite with `MagicMock(wraps=...)`)
- Environment/SysArgv for CLI entry points

**What NOT to Mock:**
- Feature computation functions (test against real data)
- Database queries (use real SQLite temp databases)
- Pandas operations (test real DataFrame transforms)

## Test Types

**Unit Tests:**
- `test_nba_client.py` — Tests rate limiting, retry logic, caching, empty response handling, static data retrieval
- `test_db.py` — Tests schema creation, upsert operations, progress tracking, dedup, WAL mode

**Integration Tests:**
- `test_ingest.py` — Tests full collection pipeline with mocked NBA client, including resumability
- `test_dnp_synthesis.py` — Tests DNP row synthesis with real DB operations
- `test_feature_pipeline.py` — End-to-end feature pipeline testing (parquet output, schema, temporal leakage, binary targets)
- `test_rolling_features.py` — Tests rolling computation against known expected values
- `test_contextual_features.py` — Tests rest days, B2B, home/away, opponent defense, matchup history

**E2E Tests:**
- Not present. No tests for FastAPI endpoints (`app.py`).

**Frontend Tests:**
- Not present. No test files in `hoopprophet/src/`.

## Key Testing Patterns

### Database Testing Pattern

Always use `tmp_db` or `feature_db` fixtures that create fresh SQLite databases:
```python
def test_upsert_player(tmp_db):
    upsert_player(tmp_db, 203999, "Nikola Jokic", True, "C", 1610612743)
    row = tmp_db.execute("SELECT * FROM players WHERE player_id = 203999").fetchone()
    assert row is not None
    assert row["full_name"] == "Nikola Jokic"
```

Use `sqlite3.Row` row factory (configured in `get_connection()`):
```python
row = tmp_db.execute(...).fetchone()
assert row["full_name"] == "Nikola Jokic"  # Access by column name
```

### Feature Computation Testing Pattern

Test three things for every feature:
1. **Column existence** — Does the function add the expected columns?
2. **Value correctness** — Do the computed values match hand-calculated expected values?
3. **Edge case handling** — Does the first game get NaN? Are DNP rows excluded?

```python
def test_rolling_averages_values_correct(feature_db):
    played = _played_logs(feature_db)
    result = compute_rolling_features(played)
    jokic = result[result["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)
    expected = jokic.loc[:4, "pts"].mean()
    assert jokic.loc[5, "pts_avg_L5"] == pytest.approx(expected)
```

### Temporal Integrity Testing Pattern

Critical pattern for ML feature engineering — verify no data leakage:
```python
def test_no_temporal_leakage_end_to_end(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)
    # Rolling features must use shift(1) internally — past data only
    # Verify by computing expected values from raw data and comparing
```

### Idempotency Testing Pattern

Verify operations that insert data are idempotent:
```python
def test_insert_game_log_dedup(tmp_db, sample_game_log_df):
    _seed_player(tmp_db)
    insert_game_logs(tmp_db, sample_game_log_df)
    count_first = tmp_db.execute("SELECT COUNT(*) FROM player_game_logs").fetchone()[0]
    insert_game_logs(tmp_db, sample_game_log_df)
    count_second = tmp_db.execute("SELECT COUNT(*) FROM player_game_logs").fetchone()[0]
    assert count_first == count_second, "INSERT OR IGNORE should prevent duplicates"
```

### Integration Test Helper Pattern

When testing processes that write to files:
```python
def _run_and_read(feature_db, tmp_path):
    output_path = tmp_path / "features.parquet"
    result = run_feature_pipeline(feature_db, output_path=str(output_path))
    df = pd.read_parquet(output_path)
    return result, output_path, df
```

## Coverage

**Requirements:** None enforced — no coverage tooling configured.

**View Coverage:**
```bash
# Not currently configured. To add:
pip install pytest-cov
pytest --cov=server.pipeline --cov-report=html
```

**Untested Areas:**
- `server/app.py` — All FastAPI endpoints (no `TestClient` tests)
- `server/ml/model_train.py` — No unit tests for model training/prediction
- `server/ml/dataset.py` — No unit tests for dataset building
- `server/ml/prop_line.py` — No unit tests for prop line retrieval
- `hoopprophet/src/` — No React component tests at all
- `server/pipeline/collectors/rosters.py` — Only tested via `test_ingest.py` integration
- `server/pipeline/collectors/schedules.py` — Only tested via `test_ingest.py` integration

---

*Testing analysis: 2026-04-17*