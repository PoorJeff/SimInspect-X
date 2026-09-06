from siminspect_localization.odometry_frame_relay import normalize_frame_id


def test_normalize_frame_id_removes_gazebo_model_scope():
    assert normalize_frame_id("siminspect_amr/odom") == "odom"
    assert normalize_frame_id("siminspect_amr/base_link") == "base_link"


def test_normalize_frame_id_preserves_normalized_and_other_frames():
    assert normalize_frame_id("odom") == "odom"
    assert normalize_frame_id("map") == "map"
    assert normalize_frame_id("other/base_link") == "other/base_link"
