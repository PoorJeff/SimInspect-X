from pathlib import Path
import importlib.util

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "firewall", ROOT / "scripts/check_ground_truth_firewall.py"
)


@pytest.mark.parametrize(
    "tag",
    [
        "depend",
        "build_depend",
        "build_export_depend",
        "buildtool_depend",
        "buildtool_export_depend",
        "exec_depend",
        "test_depend",
        "doc_depend",
        "group_depend",
    ],
)
def test_dependency_tag_is_a_violation(tmp_path, tag):
    package = tmp_path / "siminspect_bad"
    package.mkdir()
    (package / "package.xml").write_text(
        "<package><name>siminspect_bad</name>"
        f"<{tag}>siminspect_benchmark</{tag}></package>",
        encoding="utf-8",
    )
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(tmp_path) == [
        f"siminspect_bad: {tag} -> siminspect_benchmark"
    ]


def test_repository_has_no_ground_truth_dependency():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(ROOT / "src") == []
