"""Validate EKF YAML config structure and topic/TF mappings."""
import os, yaml, pytest
CFG = os.path.join(os.path.dirname(__file__), '..', 'config', 'ekf.yaml')
def test_yaml_valid():
    with open(CFG) as f: assert yaml.safe_load(f) is not None
def test_sensor_inputs():
    with open(CFG) as f:
        vals = str(yaml.safe_load(f))
    assert '/wheel/odometry' in vals
    assert '/imu/data' in vals
def test_tf_publish():
    with open(CFG) as f:
        p = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert p['publish_tf'] is True
    assert p['odom_frame'] == 'odom'
    assert p['base_link_frame'] == 'base_link'
def test_2d_mode():
    with open(CFG) as f:
        assert yaml.safe_load(f)['ekf_filter_node']['ros__parameters']['two_d_mode'] is True
