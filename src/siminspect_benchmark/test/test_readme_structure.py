"""Structural tests for README and report artifacts (P10-T03)."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def test_readme_single_quick_start():
    readme = _read("README.md")
    count = readme.count("\n## Quick Start\n")
    assert count == 1, f"expected exactly one Quick Start heading, got {count}"


def test_readme_references_artifacts():
    readme = _read("README.md")
    for token in ("run_demo.sh", "docs/report/REPORT.md",
                  "docs/report/architecture.png"):
        assert token in readme, token


def test_architecture_png_exists():
    assert os.path.exists(os.path.join(ROOT, "docs", "report",
                                       "architecture.png"))


def test_video_script_has_8_steps():
    script = _read("docs/report/demo_video_script.md")
    steps = [l for l in script.splitlines() if l.startswith("## Step")]
    assert len(steps) == 8, f"expected 8 steps, got {len(steps)}"


def test_video_script_honest_note():
    script = _read("docs/report/demo_video_script.md")
    assert "nothing in this document" in script
    assert "has been recorded" in script  # the claim being denied