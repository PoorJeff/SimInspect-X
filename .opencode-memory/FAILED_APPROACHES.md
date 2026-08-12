# Failed Approaches

Approaches that failed or were reverted, and why. Do not repeat.

## FA-001 — PowerShell double-quoted here-strings for Markdown
- Failure: PowerShell corrupts backtick code fences inside double-quoted
  here-strings; also `$` interpolation corrupts content.
- Replacement: single-quoted here-string + [System.IO.File]::WriteAllText with
  UTF8Encoding($false) (no BOM). For content heavy in backticks, use the Write
  tool instead.

## FA-002 — PowerShell `-replace` with complex regex
- Failure: arg parsing breaks on complex patterns (backslashes, parens).
- Replacement: prefer the Edit tool for exact string replacement; for bulk
  transforms write a Python script to a temp file and run it.

## FA-003 — python -c heredocs through PowerShell
- Failure: quoting/escape collisions (single quotes, backslashes, `$`) produce
  ScriptBlock parse errors or corrupted code.
- Replacement: write the Python to a temp .py via WriteAllText, then execute.

## FA-004 — unittest.mock MagicMock for rclpy modules
- Failure: `sys.modules['rclpy.node'] = MagicMock()` makes `Node` a MagicMock;
  subclassing it then calling `__new__` raises `TypeError: issubclass() arg 1
  must be a class`.
- Replacement: extract the pure logic under test into a standalone function or
  ROS-free class and test that directly (pattern used in test_handoff.py and
  test_mission_executor.py).

## FA-005 — Non-ASCII characters in YAML config
- Failure: yaml.safe_load raised UnicodeDecodeError (GBK codec) on the unicode
  multiplication sign in a comment on Windows.
- Replacement: keep all config/YAML files strict ASCII.

## FA-006 — Commit without visible acceptance criteria
- Failure: automatic guardrail blocked `git commit` twice on a multi-file
  commit until explicit Acceptance Criteria + single Current Slice were stated
  in the visible response immediately before the command.
- Replacement: always state acceptance criteria + bounded slice before the
  first mutating command of a complex task.

## FA-007 — Tests asserting geometric centre for T-cost-aware selectors
- Failure: P1/P2 selector tests expected yaw=pi (centre candidate) but the
  T-cost term (robot at origin) favours the nearest arc candidate (yaw~=2.094).
  Test expectation was wrong, not the selector.
- Replacement: assert the pose lies on the valid inspection arc
  (yaw in [2pi/3, 4pi/3]) instead of exact centre.

## FA-008 — Single pytest invocation across two ROS packages
- Failure: `pytest src/pkgA/test src/pkgB/test` fails collection with
  "import file mismatch / unique basename" because both packages ship
  test/test_dummy.py (module basename collision).
- Replacement: run each package's tests separately
  (`pytest src/pkgA/test` then `pytest src/pkgB/test`), or rename/remove
  the dummy tests before P10 cleanup.

