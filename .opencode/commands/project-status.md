---
description: Summarize current phase, next task, blockers and latest acceptance state
agent: TaskBuilder
subtask: false
---

Read the SimInspect-X project state and return only:

1. current phase;
2. last accepted task;
3. next valid TODO task;
4. blockers;
5. recommended next command.

Do not create a work slice unless explicitly requested.
