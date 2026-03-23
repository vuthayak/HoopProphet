---
phase: 1
slug: data-pipeline-caching
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | None — Wave 0 installs and creates pyproject.toml |
| **Quick run command** | `pytest server/tests/ -x --timeout=30` |
| **Full suite command** | `pytest server/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest server/tests/ -x --timeout=30`
- **After every plan wave:** Run `pytest server/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | — | setup | `pytest --version` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | DATA-01 | integration | `pytest server/tests/test_ingest.py::test_gamelogs_stored -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | DATA-02 | integration | `pytest server/tests/test_ingest.py::test_team_stats_stored -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | DATA-03 | unit | `pytest server/tests/test_nba_client.py::test_retry_backoff -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | DATA-04 | unit | `pytest server/tests/test_ingest.py::test_resume_after_interrupt -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | DATA-05 | unit | `pytest server/tests/test_dnp_synthesis.py::test_dnp_rows_created -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/tests/__init__.py` — package init
- [ ] `server/tests/conftest.py` — shared fixtures (temp SQLite db, mock nba_api responses)
- [ ] `server/tests/test_nba_client.py` — rate limiting, retry, session injection tests
- [ ] `server/tests/test_ingest.py` — game log collection, team stats, resumable progress
- [ ] `server/tests/test_dnp_synthesis.py` — zero-minute row synthesis correctness
- [ ] `pyproject.toml` or `pytest.ini` — pytest configuration
- [ ] Framework install: `pip install pytest pytest-timeout`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NBA API responds with expected data from real endpoint | DATA-01 | Live API dependency; can't mock in CI | Run `python -m server.pipeline.ingest --full` and verify SQLite row counts |
| Docker/cloud IP not blocked by NBA API | DATA-03 | Environment-specific networking | Run ingest from Docker container and check for 403/timeout errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
