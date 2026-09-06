from sensor_msgs.msg import LaserScan

from siminspect_localization.laser_scan_frame_relay import normalize_scan_frame


def test_normalize_scan_frame_preserves_scan_payload_and_rewrites_frame():
    message = LaserScan()
    message.header.frame_id = "siminspect_amr/base_link/laser_sensor"
    message.angle_min = -1.0
    message.ranges = [1.0, 2.0]
    message.intensities = [3.0, 4.0]

    normalized = normalize_scan_frame(message)

    assert normalized is not message
    assert message.header.frame_id == "siminspect_amr/base_link/laser_sensor"
    assert normalized.header.frame_id == "laser_link"
    assert normalized.angle_min == -1.0
    assert list(normalized.ranges) == [1.0, 2.0]
    assert list(normalized.intensities) == [3.0, 4.0]
