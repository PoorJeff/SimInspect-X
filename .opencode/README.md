# SimInspect-X OpenCode Runtime

This directory is **project-local OpenCode configuration**.

It complements the existing global agents such as:
- Phase-Orchestrator
- Session-Bootstrap
- Session-Handoff

It adds:

## Primary Agent
### `TaskBuilder`
Visible in the normal agent selector.

Purpose:
`Phase task -> bounded work slice -> Build handoff`

It is deliberately read-only.

## Subagent
### `Project-Auditor`
Not intended to clutter the primary-agent selector.

Purpose:
- `/verify-work`
- `/audit-work`

It is read-only and may ask permission to run test/build commands.

## Commands

- `/project-status`
- `/task-next`
- `/task-build P2-T01`
- `/work-slice`
- `/verify-work`
- `/audit-work`

## Expected workflow

```text
Phase-Orchestrator
      |
      | chooses P?-T??
      v
/task-build P?-T??
      |
      v
TaskBuilder
      |
      | returns bounded Build handoff
      v
Build
      |
      | /work-slice
      v
implementation
      |
      +--> /verify-work
      |
      +--> /audit-work
      |
      v
Phase-Orchestrator acceptance
```

## Important

`.agent/` and `.opencode/` have different roles:

- `.agent/` = project state/memory/contracts.
- `.opencode/` = OpenCode runtime agents/commands.

Do not delete either.
