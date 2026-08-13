"""Pure validation tests for the CV/SOP evidence pack (P10-T04)."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
PACK = os.path.join(ROOT, "docs", "report", "CV_EVIDENCE_PACK.md")
SOP = os.path.join(ROOT, "docs", "report", "SOP_STATEMENT.md")

EVIDENCE_PATHS = [
    "docs/report/REPORT.md",
    "docs/report/architecture.png",
    "docs/report/architecture.svg",
    "docs/report/demo_video_script.md",
    "run_demo.sh",
    "config/demo_config.yaml",
    "docs/06_ROS_TF_CONTRACT.md",
    "docs/12_EXPERIMENT_PROTOCOL.md",
    "src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/quality_scorer.py",
    "src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p2_selector.py",
    "src/siminspect_precision_control/siminspect_precision_control/pid_controller.py",
    "src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py",
    "src/siminspect_gauge_vision/siminspect_gauge_vision/vision_pipeline.py",
    "src/siminspect_gauge_vision/siminspect_gauge_vision/gauge_vision_node.py",
    "src/siminspect_mission/siminspect_mission/mission_executor.py",
    "src/siminspect_mission/siminspect_mission/report_schema.py",
    "src/siminspect_mission/siminspect_mission/mission_ordering.py",
    "src/siminspect_benchmark/siminspect_benchmark/fault_injector.py",
    "src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py",
    "src/siminspect_benchmark/siminspect_benchmark/analyze_results.py",
    "src/siminspect_benchmark/config/fault_scenarios.yaml",
    "src/siminspect_benchmark/siminspect_benchmark/run_precision_benchmark.py",
    "src/siminspect_benchmark/siminspect_benchmark/run_ablations.py",
    "src/siminspect_localization/launch/ekf.launch.py",
    "src/siminspect_navigation/launch/navigation.launch.py",
    "src/siminspect_sim/worlds/plant.sdf",
]


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _bullet_section():
    text = _read(PACK)
    start = text.index("## CV bullets")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def test_evidence_files_exist():
    for rel in EVIDENCE_PATHS:
        assert os.path.exists(os.path.join(ROOT, rel)), rel


def test_sop_exists_and_honest():
    sop = _read(SOP)
    assert "simulation-first" in sop
    assert "Claim boundary" in sop
    assert "pending" in sop.lower()
    words = len(sop.split())
    assert 150 <= words <= 220, words


def test_bullets_have_pending_markers():
    section = _bullet_section()
    assert "[pending" in section


def test_bullets_have_no_filled_percentages():
    section = _bullet_section()
    assert re.search(r"\d+\s*%", section) is None


def test_bullets_have_no_verb_number_pattern():
    section = _bullet_section()
    assert re.search(r"(improved|reduced|reducing|improving|raising)\s+\S*\d",
                     section) is None


def test_skills_matrix_covers_ntu_themes():
    pack = _read(PACK)
    for theme in ("Advanced Robotics", "Sensors and Data Fusion",
                  "Autonomous Mobile Robot", "Machine Vision",
                  "Advanced Linear Systems", "Digital Twin",
                  "Manufacturing Control", "Multivariable Control"):
        assert theme in pack, theme