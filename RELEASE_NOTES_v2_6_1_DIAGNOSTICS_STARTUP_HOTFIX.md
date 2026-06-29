# ATIS CLEAN OPERATIONAL v2.6.1 — Diagnostics Startup Hotfix

## Fixed
- Diagnostics tab no longer crashes during startup.
- Guarded `self.status.setText()` so it only runs after the status label exists.

## Preserved
- Phase 16 diagnostics
- Regression smoke script
- One top search bar
