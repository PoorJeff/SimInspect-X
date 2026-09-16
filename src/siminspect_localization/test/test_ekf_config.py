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

def test_imu_fuses_rate_without_overriding_wheel_pose_heading():
    with open(CFG) as f:
        p = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    imu = p['imu0_config']
    # Gazebo provides absolute orientation in the sensor/world convention;
    # wheel odometry is the pose source. Fuse only angular velocity so EKF
    # cannot create a second heading frame during turns.
    assert imu[3:6] == [False, False, False]
    assert imu[11] is True

def test_wheel_odometry_pose_constrains_ekf_drift():
    with open(CFG) as f:
        p = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    odom = p['odom0_config']
    assert odom[0] is True
    assert odom[1] is True
    assert odom[5] is True
