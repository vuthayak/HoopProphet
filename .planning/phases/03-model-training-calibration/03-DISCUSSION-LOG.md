# Phase 3: Model Training & Calibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 03-model-training-calibration
**Areas discussed:** Calibration strategy

---

## Calibration strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Isotonic only | Always isotonic; fail if too sparse | |
| Isotonic + Platt fallback | Prefer isotonic; fall back to Platt when unreliable; log method | ✓ |
| Isotonic + threshold gate | Isotonic only above a threshold; else stop (no fallback) | |

**User's choice:** Option 2 — Isotonic preferred + automatic Platt fallback.

**Notes:** Aligns with MODL-03 (isotonic via CalibratedClassifierCV-style workflow) while allowing a documented fallback when validation support is insufficient for stable isotonic curves.

---

## Claude's Discretion

*(none recorded for this session)*

## Deferred Ideas

*(none)*
