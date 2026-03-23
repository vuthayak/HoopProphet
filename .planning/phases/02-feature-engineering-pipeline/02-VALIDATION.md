---
phase: 2
slug: feature-engineering-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | None (uses defaults; tests in `server/tests/`) |
| **Quick run command** | `python -m pytest server/tests/test_features.py -x` |
| **Full suite command** | `python -m pytest server/tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest server/tests/test_features.py -x`
- **After every plan wave:** Run `python -m pytest server/tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | FEAT-01 | unit | `python -m pytest server/tests/test_features.py::test_rolling_averages -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | FEAT-02 | unit | `python -m pytest server/tests/test_features.py::test_rolling_std -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | FEAT-03 | unit | `python -m pytest server/tests/test_features.py::test_opponent_features -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | FEAT-04 | unit | `python -m pytest server/tests/test_features.py::test_rest_days -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | FEAT-05 | unit | `python -m pytest server/tests/test_features.py::test_home_away -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | FEAT-06 | unit | `python -m pytest server/tests/test_features.py::test_pace_features -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | FEAT-07 | unit | `python -m pytest server/tests/test_features.py::test_minutes_trend -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 0 | FEAT-08 | unit | `python -m pytest server/tests/test_features.py::test_matchup_history -x` | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 0 | FEAT-09 | integration | `python -m pytest server/tests/test_features.py::test_no_leakage -x` | ❌ W0 | ⬜ pending |
| 02-01-10 | 01 | 0 | FEAT-10 | integration | `python -m pytest server/tests/test_features.py::test_parquet_output -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/tests/test_features.py` — stubs for FEAT-01 through FEAT-10
- [ ] Extend `server/tests/conftest.py` — add fixtures for multi-game, multi-player, multi-season test data with known expected rolling values

*Wave 0 creates test infrastructure before feature code is written.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
