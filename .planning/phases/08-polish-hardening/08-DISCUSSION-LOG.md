# Phase 8: Polish & Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-22
**Phase:** 08-polish-hardening
**Mode:** discuss
**Areas discussed:** V1 Code Removal, Git & Build Hygiene, Docker & Deployment Hardening, Error Response Audit, Dead Code Sweep, SPA Routing Fallback, Test & Validation

## Discussion Q&A

### V1 Code Removal
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| How thorough should V1 code removal be? | Full removal (delete server/ml/) / Minimal (Gemini only) / Full removal + V2 audit | Full removal + V2 audit |
| Delete server/data/nba.db (0-byte V1 remnant)? | Yes, delete nba.db only / No, leave all data files | Yes, delete nba.db only |

### Git & Build Hygiene
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| How thorough should git cleanup be? | Full git cleanup (git rm dist/, update .gitignore, clean __pycache__) / Targeted cleanup only | Full git cleanup |

### Docker & Deployment Hardening
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| Docker Compose tightening scope? | Essential hardening (remove GEMINI_API_KEY, tighten CORS) / Essential + production readiness / Minimal (env var only) | Essential hardening |

### Error Response Audit
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| Audit V2 API error responses for information leakage? | Yes, audit V2 error responses / Skip — V2 is clean enough | Yes, audit V2 error responses |

### Dead Code Sweep
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| Broader dead code audit beyond server/ml/? | Yes, broader dead code sweep / Just V1 removal — don't expand scope | Yes, broader dead code sweep |

### SPA Routing Fallback (folded from Phase 7)
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| Fold Phase 7 plan 07-05 (SPA routing) into Phase 8? | Yes, fold it in / No, keep in Phase 7 | Yes, fold it in |

### Test & Validation
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| How thorough should validation be? | Extended V1 cleanup tests / Existing tests are fine / Full audit validation suite | Full audit validation suite |

### Logging
| Question | Options Presented | User Selection |
|----------|-----------------|---------------|
| Audit V2 code for print() vs logging? | Yes, audit V2 logging / Skip — V2 logging is fine | Skip — V2 logging is fine |

---

*Phase: 08-polish-hardening*
*Log gathered: 2026-04-22*