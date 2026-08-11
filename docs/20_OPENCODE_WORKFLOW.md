# OpenCode Workflow

## Why TaskBuilder is project-local

The global Phase-Orchestrator decides **what project task is next**.
TaskBuilder decides **how to make that task small enough for one implementation session**.

This prevents:
- phase-level prompts being too broad;
- Build silently redesigning architecture;
- verification criteria being invented after implementation;
- long sessions drifting into the next task.

## Normal use

### 1. Orchestrator
Tell Phase-Orchestrator:
`继续`

or ask it to select the next task.

### 2. TaskBuilder
Run:
```text
/task-build P2-T01
```

or:
```text
/task-next
```

### 3. Build
Switch to Build and run:
```text
/work-slice
```

### 4. Verify
Run:
```text
/verify-work
```

### 5. Audit
Run:
```text
/audit-work
```

### 6. Acceptance
Return the verifier/auditor result to Phase-Orchestrator.
Only the orchestrator should advance project state/acceptance.

## New work session

Use the existing global `Session-Bootstrap` / `Session-Handoff` agents together with:
- `.agent/HANDOFF.md`
- `.agent/PROJECT_STATE.md`
- `.agent/TASK_LEDGER.md`

TaskBuilder should never be used as the implementation agent.
