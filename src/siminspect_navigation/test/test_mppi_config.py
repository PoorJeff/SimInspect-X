"""Validate MPPI controller configuration in nav2_params.yaml."""
import os, yaml, pytest
CFG = os.path.join(os.path.dirname(__file__), "..", "config", "nav2_params.yaml")

def test_controller_is_mppi():
    with open(CFG) as f:
        data = yaml.safe_load(f)
    cs = data["controller_server"]["ros__parameters"]
    fw = cs["FollowPath"]
    assert "mppi" in fw["plugin"].lower(), f"Expected MPPI, got {fw["plugin"]}"

def test_motion_model_diffdrive():
    with open(CFG) as f:
        data = yaml.safe_load(f)
    fw = data["controller_server"]["ros__parameters"]["FollowPath"]
    assert fw["motion_model"] == "DiffDrive"

def test_four_critics():
    with open(CFG) as f:
        data = yaml.safe_load(f)
    fw = data["controller_server"]["ros__parameters"]["FollowPath"]
    critics = fw.get("critic_plugins", [])
    assert len(critics) >= 4, f"Expected >=4 critics, got {len(critics)}"
    for c in ["PathFollow", "PathAngle", "GoalCritic", "Obstacles"]:
        assert c in critics, f"Missing critic: {c}"

def test_velocity_limits():
    with open(CFG) as f:
        data = yaml.safe_load(f)
    fw = data["controller_server"]["ros__parameters"]["FollowPath"]
    assert fw["max_vel_x"] > 0
    assert fw["max_vel_theta"] > 0

def test_goals_exist():
    gf = os.path.join(os.path.dirname(__file__), "..", "config", "mppi_test_goals.yaml")
    assert os.path.exists(gf), "mppi_test_goals.yaml not found"
    with open(gf) as f:
        data = yaml.safe_load(f)
    assert len(data["goals"]) >= 3
