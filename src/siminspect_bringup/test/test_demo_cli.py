import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.demo_orchestrator import (  # noqa: E402
    _git_metadata,
    _has_map_odom_transform,
    _output_text,
    _tf2_echo_has_map_odom,
    _topic_has_publisher,
    build_parser,
    config_with_overrides,
)


def test_help_and_public_modes_are_explicit():
    parser = build_parser()
    help_text = parser.format_help()
    assert "--headless" in help_text and "--visual" in help_text and "--record" in help_text
    assert "--benchmark-evidence" in help_text
    assert "--method" in help_text and "--scenario" in help_text and "--seed" in help_text


def test_record_requires_visual_and_overrides_are_forwarded():
    args = parser_args = build_parser().parse_args(["--visual", "--record", "--method", "P2", "--scenario", "F07", "--seed", "21"])
    assert args.visual and args.record
    config = config_with_overrides(ROOT / "config" / "demo_config.yaml", args)
    assert config.method == "P2"
    assert config.scenario == "F07"
    assert config.seed == 21
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--headless", "--record"])


def test_benchmark_flag_is_internal_and_headless_defaults_without_tty():
    args = build_parser().parse_args(["--headless", "--benchmark-evidence", "--artifact-root", "runs"])
    assert args.benchmark_evidence is True
    assert args.artifact_root == Path("runs")
    assert args.visual is False


def test_container_can_receive_commit_provenance_without_git(monkeypatch, tmp_path):
    monkeypatch.setenv("SIMINSPECT_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("SIMINSPECT_GIT_DIRTY", "0")
    assert _git_metadata(tmp_path) == ("a" * 40, False)


def test_navigation_readiness_parsers_require_map_publisher_and_tf_edge():
    assert _topic_has_publisher("Publisher count: 1")
    assert not _topic_has_publisher("Publisher count: 0")
    assert _has_map_odom_transform("frame_id: map\nchild_frame_id: odom\n")
    assert not _has_map_odom_transform("frame_id: odom\nchild_frame_id: base_link\n")
    assert _tf2_echo_has_map_odom("Translation: [0.0, 0.0, 0.0]\nRotation: in Quaternion")
    assert _tf2_echo_has_map_odom(b"Translation: [0.0, 0.0, 0.0]\nRotation: in Quaternion")
    assert not _tf2_echo_has_map_odom("Waiting for transform map -> odom")


def test_timeout_output_is_json_safe_text():
    assert _output_text(b"Waiting for transform") == "Waiting for transform"
    assert _output_text(None) == ""
