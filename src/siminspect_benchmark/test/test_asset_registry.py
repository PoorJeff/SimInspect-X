from siminspect_benchmark.asset_registry import asset_from_dict


def test_asset_from_dict_casts_yaml_numbers_for_ros_float_fields():
    asset = asset_from_dict(
        {
            "id": "gauge_test",
            "asset_type": "analog_gauge",
            "map_pose": {"x": 2, "y": 3, "z": 1, "yaw": 0},
            "gauge": {"min_value": 0, "max_value": 50, "unit": "bar"},
        }
    )

    assert isinstance(asset.map_pose.position.x, float)
    assert isinstance(asset.map_pose.position.y, float)
    assert isinstance(asset.map_pose.position.z, float)
    assert isinstance(asset.min_value, float)
    assert isinstance(asset.max_value, float)
