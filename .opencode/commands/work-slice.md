---
description: Implement the current bounded work slice in Build
agent: build
subtask: false
---

Implement only the current approved SimInspect-X work slice.

Before editing:
- read `AGENTS.md`;
- read `.agent/PROJECT_STATE.md`;
- read `.agent/TASK_LEDGER.md`;
- read `.agent/DECISIONS.md`;
- read the relevant phase and technical docs;
- preserve the TaskBuilder acceptance criteria.

Rules:
- do not advance to another task;
- do not change architecture without an ADR/orchestrator decision;
- add/update tests together with implementation;
- run relevant verification before stopping;
- do not mark the task ACCEPTED yourself.

Additional user arguments:
`$ARGUMENTS`
