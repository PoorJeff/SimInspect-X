# Project Memory Index

## HOT Memory (always load)
- `CURRENT_CONTEXT.md` — current goal, phase, architecture, next action

## WARM Memory (load on demand)
- `DECISIONS.md` — durable architectural decisions (D-001..D-010)
- `OPEN_ISSUES.md` — blockers and unresolved problems (OI-001/002 RESOLVED, OI-003..OI-006 open)
- `FAILED_APPROACHES.md` — what did not work and why (FA-001..FA-008)

## COLD Memory (session history)
- `SESSION_HISTORY/S001.md` — P0-P6 initial build session
- `SESSION_HISTORY/S002.md` — P6-T05 wrap-up + P7 full + P8-T01 (2026-08-13)
- `SESSION_HISTORY/S003.md` — P8-T01 closure: C2 fix, audit, push (2026-08-13)

## Last Updated
2026-08-13 — S003 closed: 35/55 ACCEPTED, remote main = dc8cb7b (synced),
working tree clean; P8-T02 next

## Navigation quick facts
- Task ledger: `.agent/TASK_LEDGER.md`
- Phase state: `.agent/PROJECT_STATE.md` (P8_IN_PROGRESS)
- Benchmark outputs: `results/`
- Windows-testable packages: precision_control (33 tests), mission (12 tests) —
  run packages separately (FA-008: test_dummy.py basename collision)
- Push: works with VPN active
