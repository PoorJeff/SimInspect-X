from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    ".opencode/agents/TaskBuilder.md",
    ".opencode/agents/Project-Auditor.md",
    ".opencode/commands/task-build.md",
    ".opencode/commands/task-next.md",
    ".opencode/commands/work-slice.md",
    ".opencode/commands/verify-work.md",
    ".opencode/commands/audit-work.md",
    ".opencode/commands/project-status.md",
]

errors = []
for rel in required:
    p = ROOT / rel
    if not p.exists():
        errors.append(f"missing: {rel}")
        continue
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errors.append(f"missing frontmatter: {rel}")

task = (ROOT / ".opencode/agents/TaskBuilder.md").read_text(encoding="utf-8")
if "mode: primary" not in task:
    errors.append("TaskBuilder must be mode: primary")
if "edit: deny" not in task:
    errors.append("TaskBuilder must remain read-only")

aud = (ROOT / ".opencode/agents/Project-Auditor.md").read_text(encoding="utf-8")
if "mode: subagent" not in aud:
    errors.append("Project-Auditor must be mode: subagent")
if "edit: deny" not in aud:
    errors.append("Project-Auditor must remain read-only")

if errors:
    print("OpenCode runtime validation FAILED")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("OpenCode runtime validation PASSED")
print("TaskBuilder: primary/read-only")
print("Project-Auditor: subagent/read-only")
print("Commands:", 6)
