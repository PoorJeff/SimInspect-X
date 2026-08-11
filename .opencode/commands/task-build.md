---
description: Turn one project task into a bounded Build work slice
agent: TaskBuilder
subtask: false
---

Build a work slice for `$ARGUMENTS`.

If `$ARGUMENTS` is empty, determine the next valid TODO task from the current phase and project state.
Follow the TaskBuilder output contract exactly.
