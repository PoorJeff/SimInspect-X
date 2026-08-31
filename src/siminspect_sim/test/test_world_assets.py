"""Contracts for installable, camera-visible Gazebo gauge assets."""
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import yaml


SIM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = REPO_ROOT / "src" / "siminspect_assets" / "assets"
DESCRIPTION_DIR = REPO_ROOT / "src" / "siminspect_description"
VISION_PACKAGE_ROOT = REPO_ROOT / "src" / "siminspect_gauge_vision"
MODEL_DIR = SIM_DIR / "models" / "gauge_asset"
if str(VISION_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(VISION_PACKAGE_ROOT))

from siminspect_gauge_vision.vision_pipeline import run_pipeline  # noqa: E402


def _registry():
    records = {}
    for path in sorted(ASSET_DIR.glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        records[record["id"]] = record
    assert len(records) == 6
    return records


def _world_root():
    return ET.parse(SIM_DIR / "worlds" / "plant.sdf").getroot()


def _gauge_includes():
    includes = []
    for include in _world_root().findall(".//include"):
        if include.findtext("uri", "").strip() == "model://gauge_asset":
            includes.append(include)
    return includes


def _pose_values(element):
    return tuple(float(value) for value in element.findtext("pose").split())


def _camera_contract():
    spawn_launch = (
        DESCRIPTION_DIR / "launch" / "robot_spawn.launch.py"
    ).read_text(encoding="utf-8")
    spawn_match = re.search(r'"-z",\s*"([0-9.]+)"', spawn_launch)
    assert spawn_match is not None

    urdf = ET.parse(
        DESCRIPTION_DIR / "urdf" / "siminspect.urdf.xacro"
    ).getroot()
    camera_joint = urdf.find(".//joint[@name='camera_joint']/origin")
    assert camera_joint is not None

    gazebo = ET.parse(
        DESCRIPTION_DIR / "urdf" / "siminspect.gazebo.xacro"
    ).getroot()
    camera = gazebo.find(".//sensor[@name='camera_sensor']/camera")
    assert camera is not None

    return {
        "spawn_z": float(spawn_match.group(1)),
        "joint_xyz": tuple(
            float(value) for value in camera_joint.attrib["xyz"].split()),
        "hfov": float(camera.findtext("horizontal_fov")),
        "width": int(camera.findtext("image/width")),
        "height": int(camera.findtext("image/height")),
        "near_clip": float(camera.findtext("clip/near")),
    }


def test_sim_package_is_colcon_discoverable_and_registers_world_test():
    manifest = ET.parse(SIM_DIR / "package.xml").getroot()
    assert manifest.findtext("name") == "siminspect_sim"
    cmake = " ".join(
        (SIM_DIR / "CMakeLists.txt").read_text(encoding="utf-8").split())
    assert "project(siminspect_sim)" in cmake
    assert "ament_package()" in cmake
    assert "ament_add_pytest_test(test_world_assets test/test_world_assets.py)" in cmake


def test_sim_package_installs_world_models_and_resource_environment_hook():
    cmake = " ".join(
        (SIM_DIR / "CMakeLists.txt").read_text(encoding="utf-8").split())
    assert "install(DIRECTORY worlds models DESTINATION share/${PROJECT_NAME})" in cmake
    assert "ament_environment_hooks(" in cmake
    hook = (SIM_DIR / "env-hooks" / "siminspect_sim.dsv.in")
    assert hook.read_text(encoding="utf-8").strip() == (
        "prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;"
        "share/siminspect_sim/models"
    )


def test_world_has_exactly_the_six_registry_gauge_instances():
    registry_ids = set(_registry())
    names = [include.findtext("name", "").strip()
             for include in _gauge_includes()]
    assert len(names) == 6
    assert len(names) == len(set(names))
    assert set(names) == registry_ids


def test_world_gauge_instance_poses_match_registry():
    registry = _registry()
    includes = {
        include.findtext("name").strip(): include
        for include in _gauge_includes()
    }
    assert set(includes) == set(registry)
    for asset_id, record in registry.items():
        pose = _pose_values(includes[asset_id])
        expected = (
            float(record["map_pose"]["x"]),
            float(record["map_pose"]["y"]),
            float(record["map_pose"]["z"]),
            0.0,
            0.0,
            float(record["map_pose"]["yaw"]),
        )
        assert len(pose) == 6
        assert all(math.isclose(actual, wanted, abs_tol=1e-3)
                   for actual, wanted in zip(pose, expected)), (
                       asset_id, pose, expected)


def test_supported_faces_point_outward_and_do_not_start_inside_obstacles():
    includes = {
        include.findtext("name").strip(): include
        for include in _gauge_includes()
    }
    world_models = {
        model.attrib["name"]: model
        for model in _world_root().findall(".//model")
    }
    support_models = {
        "gauge_tank_01": "tank_1",
        "gauge_tank_02": "tank_2",
        "gauge_pipe_02": "pipe_2",
    }
    gauge_model = ET.parse(MODEL_DIR / "model.sdf").getroot()
    housing = gauge_model.find(".//visual[@name='housing']")
    assert housing is not None
    housing_rear_x = (
        _pose_values(housing)[0]
        - float(housing.findtext("geometry/cylinder/length")) / 2.0
    )
    support_clearance = 0.005

    for asset_id, support_name in support_models.items():
        face_pose = _pose_values(includes[asset_id])
        support = world_models[support_name]
        support_pose = _pose_values(support)
        radius = float(
            support.findtext(".//collision/geometry/cylinder/radius"))
        normal = (math.cos(face_pose[5]), math.sin(face_pose[5]))
        offset = (
            face_pose[0] - support_pose[0],
            face_pose[1] - support_pose[1],
        )
        outward_distance = offset[0] * normal[0] + offset[1] * normal[1]
        lateral_offset = abs(
            offset[0] * normal[1] - offset[1] * normal[0])
        assert lateral_offset <= 1e-3, (asset_id, lateral_offset)
        assert outward_distance + 1e-3 >= radius, (
            asset_id, outward_distance, radius)
        support_surface_x = radius - outward_distance
        assert support_surface_x <= housing_rear_x - support_clearance + 1e-6, (
            asset_id, support_surface_x, housing_rear_x)


def test_world_primitives_use_sdf_child_elements():
    root = _world_root()
    boxes = root.findall(".//box")
    cylinders = root.findall(".//cylinder")
    assert boxes
    assert cylinders

    for box in boxes:
        assert "size" not in box.attrib
        assert box.findtext("size", "").strip()
    for cylinder in cylinders:
        assert "radius" not in cylinder.attrib
        assert "length" not in cylinder.attrib
        assert cylinder.findtext("radius", "").strip()
        assert cylinder.findtext("length", "").strip()


def test_gauge_face_origin_normal_size_and_texture_contract():
    config = ET.parse(MODEL_DIR / "model.config").getroot()
    assert config.findtext("name") == "gauge_asset"
    assert config.findtext("sdf") == "model.sdf"

    model = ET.parse(MODEL_DIR / "model.sdf").getroot()
    face = model.find(".//visual[@name='gauge_face']")
    assert face is not None
    assert _pose_values(face) == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert tuple(float(v) for v in face.findtext("geometry/plane/normal").split()) == (
        1.0, 0.0, 0.0)
    assert tuple(float(v) for v in face.findtext("geometry/plane/size").split()) == (
        0.32, 0.32)
    texture_uri = face.findtext("material/pbr/metal/albedo_map")
    assert texture_uri == (
        "model://gauge_asset/materials/textures/gauge_face.png")
    assert (MODEL_DIR / "materials" / "textures" / "gauge_face.png").is_file()

    face_x = _pose_values(face)[0]
    housings = (
        model.find(".//visual[@name='housing']"),
        model.find(".//collision[@name='housing_collision']"),
    )
    for housing in housings:
        assert housing is not None
        housing_x = _pose_values(housing)[0]
        housing_length = float(
            housing.findtext("geometry/cylinder/length"))
        assert housing_x + housing_length / 2.0 < face_x


def test_canonical_texture_passes_detector_confidence_contract_only():
    texture = MODEL_DIR / "materials" / "textures" / "gauge_face.png"
    image = cv2.imread(str(texture), cv2.IMREAD_COLOR)
    assert image is not None
    assert image.shape == (320, 320, 3)
    result = run_pipeline(image, asset_id="canonical_texture")
    assert result["confidence"] >= 0.80
    assert result["view_angle_proxy"] == 1.0


def test_nominal_camera_projection_passes_default_detector_contract():
    camera = _camera_contract()
    assert (camera["width"], camera["height"]) == (640, 480)

    face_radius_m = 0.16
    camera_to_face_m = 0.8 - camera["joint_xyz"][0]
    focal_length_px = camera["width"] / (
        2.0 * math.tan(camera["hfov"] / 2.0))
    projected_radius_px = focal_length_px * face_radius_m / camera_to_face_m
    diameter_px = round(2.0 * projected_radius_px)

    texture = cv2.imread(
        str(MODEL_DIR / "materials" / "textures" / "gauge_face.png"),
        cv2.IMREAD_COLOR,
    )
    assert texture is not None
    projected = cv2.resize(
        texture, (diameter_px, diameter_px), interpolation=cv2.INTER_AREA)
    frame = np.full(
        (camera["height"], camera["width"], 3), 127, dtype=np.uint8)
    x0 = (camera["width"] - diameter_px) // 2
    y0 = (camera["height"] - diameter_px) // 2
    frame[y0:y0 + diameter_px, x0:x0 + diameter_px] = projected

    result = run_pipeline(frame, asset_id="nominal_camera_projection")
    assert result["confidence"] >= 0.80
    assert result["view_angle_proxy"] == 1.0


def test_all_candidate_footprints_fit_inside_expanded_enclosure():
    walls = {
        model.attrib["name"]: model
        for model in _world_root().findall(".//model")
        if model.attrib.get("name", "").startswith("wall_")
    }
    assert set(walls) == {"wall_north", "wall_south", "wall_east", "wall_west"}
    assert _pose_values(walls["wall_north"])[1] == 9.0
    assert _pose_values(walls["wall_south"])[1] == -9.0
    assert _pose_values(walls["wall_east"])[0] == 9.0
    assert _pose_values(walls["wall_west"])[0] == -9.0
    for wall in walls.values():
        size = tuple(float(v) for v in wall.findtext(".//box/size").split())
        assert size[:2] == (18.0, 0.2)

    inner_limit = 9.0 - 0.2 / 2.0
    footprint_radius = 0.25
    half_arc = math.radians(120.0 / 2.0)
    for record in _registry().values():
        x = float(record["map_pose"]["x"])
        y = float(record["map_pose"]["y"])
        yaw = float(record["map_pose"]["yaw"])
        for index in range(7):
            angle = yaw - half_arc + index * (2.0 * half_arc / 6.0)
            candidate_x = x + 0.8 * math.cos(angle)
            candidate_y = y + 0.8 * math.sin(angle)
            assert abs(candidate_x) + footprint_radius <= inner_limit
            assert abs(candidate_y) + footprint_radius <= inner_limit


def test_all_gauge_face_corners_fit_every_candidate_camera_view():
    camera = _camera_contract()
    spawn_z = camera["spawn_z"]
    camera_joint_xyz = camera["joint_xyz"]
    hfov = camera["hfov"]
    width = camera["width"]
    height = camera["height"]
    assert (width, height) == (640, 480)

    camera_z = spawn_z + camera_joint_xyz[2]
    horizontal_limit = math.tan(hfov / 2.0)
    vertical_fov = 2.0 * math.atan(math.tan(hfov / 2.0) * height / width)
    vertical_limit = math.tan(vertical_fov / 2.0)
    near_clip = camera["near_clip"]
    face_radius = 0.16
    standoff = 0.8
    half_arc = math.radians(120.0 / 2.0)
    for asset_id, record in _registry().items():
        gauge_x = float(record["map_pose"]["x"])
        gauge_y = float(record["map_pose"]["y"])
        gauge_z = float(record["map_pose"]["z"])
        gauge_yaw = float(record["map_pose"]["yaw"])
        face_tangent = (-math.sin(gauge_yaw), math.cos(gauge_yaw))

        for candidate_index in range(7):
            candidate_angle = (
                gauge_yaw - half_arc
                + candidate_index * (2.0 * half_arc / 6.0))
            base_x = gauge_x + standoff * math.cos(candidate_angle)
            base_y = gauge_y + standoff * math.sin(candidate_angle)
            robot_yaw = candidate_angle + math.pi
            forward = (math.cos(robot_yaw), math.sin(robot_yaw))
            lateral = (-math.sin(robot_yaw), math.cos(robot_yaw))
            camera_x = (base_x + camera_joint_xyz[0] * forward[0]
                        + camera_joint_xyz[1] * lateral[0])
            camera_y = (base_y + camera_joint_xyz[0] * forward[1]
                        + camera_joint_xyz[1] * lateral[1])

            for tangent_sign in (-1.0, 1.0):
                corner_x = gauge_x + tangent_sign * face_radius * face_tangent[0]
                corner_y = gauge_y + tangent_sign * face_radius * face_tangent[1]
                relative_x = corner_x - camera_x
                relative_y = corner_y - camera_y
                depth = relative_x * forward[0] + relative_y * forward[1]
                horizontal = (
                    relative_x * lateral[0] + relative_y * lateral[1])

                for vertical_sign in (-1.0, 1.0):
                    vertical = (
                        gauge_z + vertical_sign * face_radius - camera_z)
                    context = (
                        asset_id, candidate_index,
                        tangent_sign, vertical_sign,
                        horizontal, vertical, depth)
                    assert depth > near_clip, context
                    assert abs(horizontal / depth) <= horizontal_limit, context
                    assert abs(vertical / depth) <= vertical_limit, context
