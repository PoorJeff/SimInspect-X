#!/usr/bin/env bash
# SimInspect-X one-command demo (P10-T01).
#
# Host mode (default): ensure the Docker image exists (build if missing),
# then run this script inside the container with the workspace mounted.
# In-container mode (--in-docker): stage-launch the full inspection chain
# headlessly and wait for the mission report.
#
# World file locations (verified):
#   plant.sdf        -> src/siminspect_sim/worlds/
#   blocked_test.sdf -> src/siminspect_navigation/worlds/
#
# Honest scope: this script has NOT been runtime-validated on Windows.
# Runtime validation requires the Ubuntu 24.04 container (OI-005).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="siminspect-x"
WORKSPACE_MOUNT="/home/siminspect/workspace"
CONFIG_FILE="config/demo_config.yaml"

usage() {
    echo "Usage:"
    echo "  ./run_demo.sh              # host mode: build image if needed, run demo in container"
    echo "  ./run_demo.sh --build      # force image rebuild"
    echo "  ./run_demo.sh --in-docker  # run inside the container (invoked by host mode)"
    exit 1
}

if [ "${1:-}" = "--in-docker" ]; then
    # ------------------ in-container mode ------------------
    source /opt/ros/jazzy/setup.bash || { echo "ERROR: ROS 2 Jazzy not found" >&2; exit 1; }
    if [ ! -f install/setup.bash ]; then
        echo "[setup] workspace not built; running setup.sh ..."
        bash setup.sh
    fi
    source install/setup.bash

    DEMO_SEED=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['seed'])")
    DEMO_ORDERING=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['ordering'])")
    DEMO_TIMEOUT=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['timeout_s'])")
    DEMO_WORLD=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['world'])")

    PIDS=()
    cleanup() {
        echo "[demo] shutting down background processes..."
        for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    }
    trap cleanup EXIT

    stage() {
        echo "[demo] $1"
        sleep "${2:-3}"
    }

    echo "=== SimInspect-X one-command demo ==="
    echo "world=$DEMO_WORLD ordering=$DEMO_ORDERING seed=$DEMO_SEED timeout=${DEMO_TIMEOUT}s"

    stage "starting headless Gazebo + robot (gui=false)" 5
    ros2 launch siminspect_description robot_spawn.launch.py \
        world:="$DEMO_WORLD" gui:=false > /tmp/demo_gz.log 2>&1 &
    PIDS+=($!)

    stage "starting EKF" 5
    ros2 launch siminspect_localization ekf.launch.py > /tmp/demo_ekf.log 2>&1 &
    PIDS+=($!)

    stage "starting SLAM" 8
    ros2 launch siminspect_localization slam.launch.py > /tmp/demo_slam.log 2>&1 &
    PIDS+=($!)

    stage "starting Nav2" 8
    ros2 launch siminspect_navigation navigation.launch.py > /tmp/demo_nav.log 2>&1 &
    PIDS+=($!)

    stage "starting precision approach (PID)" 5
    ros2 launch siminspect_precision_control precision_approach.launch.py \
        > /tmp/demo_pa.log 2>&1 &
    PIDS+=($!)

    stage "starting viewpoint planner (candidates + P2 selector)" 5
    ros2 run siminspect_viewpoint_planner candidate_generator.py \
        > /tmp/demo_cg.log 2>&1 &
    PIDS+=($!)
    ros2 run siminspect_viewpoint_planner p2_selector.py > /tmp/demo_p2.log 2>&1 &
    PIDS+=($!)

    stage "starting gauge vision node (P10-T01: closes P5 wiring debt)" 3
    ros2 run siminspect_gauge_vision gauge_vision_node.py \
        > /tmp/demo_vision.log 2>&1 &
    PIDS+=($!)

    stage "starting asset registry" 3
    ros2 run siminspect_benchmark asset_registry.py > /tmp/demo_assets.log 2>&1 &
    PIDS+=($!)

    stage "starting fault injector (F00 nominal, fixed seed)" 3
    ros2 run siminspect_benchmark fault_injector.py --ros-args \
        -p scenario:=F00 -p seed:="$DEMO_SEED" > /tmp/demo_fault.log 2>&1 &
    PIDS+=($!)

    stage "starting mission executor (ordering=$DEMO_ORDERING)" 5
    ros2 run siminspect_mission mission_executor.py --ros-args \
        -p ordering:="$DEMO_ORDERING" > /tmp/demo_mission.log 2>&1 &
    PIDS+=($!)

    echo "[demo] waiting for mission completion (timeout ${DEMO_TIMEOUT}s)..."
    elapsed=0
    while [ "$elapsed" -lt "$DEMO_TIMEOUT" ]; do
        if [ -f mission_report.json ]; then
            echo "[demo] mission_report.json detected after ${elapsed}s"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if [ ! -f mission_report.json ]; then
        echo "ERROR: mission did not complete within ${DEMO_TIMEOUT}s" >&2
        echo "Last log lines (mission):" >&2
        tail -n 20 /tmp/demo_mission.log >&2 || true
        exit 1
    fi

    echo "=== Demo result summary ==="
    python3 - <<'PYEOF'
import json
report = json.load(open("mission_report.json"))
print(f"schema_version : {report.get('schema_version')}")
print(f"num_assets     : {report.get('num_assets')}")
print(f"num_results    : {report.get('num_results')}")
print(f"success_count  : {report.get('success_count')}")
for r in report.get("results", []):
    print(f"  {r['asset_id']:16s} status={r['status']:8s} "
          f"conf={r.get('confidence')} est={r.get('estimated_value')} "
          f"reason={r.get('failure_reason')}")
PYEOF

    echo "[demo] report exported to mission_report.json"
    exit 0
fi

# ------------------ host mode ------------------
if [ "${1:-}" = "--build" ]; then
    echo "[host] building image $IMAGE_NAME ..."
    docker build -t "$IMAGE_NAME" docker/
else
    if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
        echo "[host] image $IMAGE_NAME not found; building ..."
        docker build -t "$IMAGE_NAME" docker/
    fi
fi

echo "[host] running demo inside container (workspace mounted at $WORKSPACE_MOUNT)"
docker run --rm -it \
    -v "$SCRIPT_DIR:$WORKSPACE_MOUNT" \
    "$IMAGE_NAME" bash -c \
    "cd $WORKSPACE_MOUNT && ./run_demo.sh --in-docker"