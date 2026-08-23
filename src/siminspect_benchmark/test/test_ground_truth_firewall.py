from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "firewall", ROOT / "scripts/check_ground_truth_firewall.py"
)


def test_exec_depend_is_a_violation(tmp_path):
    package = tmp_path / "siminspect_bad"
    package.mkdir()
    (package / "package.xml").write_text(
        "<package><name>siminspect_bad</name>"
        "<exec_depend>siminspect_benchmark</exec_depend></package>",
        encoding="utf-8",
    )
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(tmp_path) == [
        "siminspect_bad: exec_depend -> siminspect_benchmark"
    ]


def test_repository_has_no_ground_truth_dependency():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(ROOT / "src") == []
