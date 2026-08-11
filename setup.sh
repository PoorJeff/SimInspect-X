#!/usr/bin/env bash
set -euo pipefail

# SimInspect-X workspace setup
# Run from repository root after cloning.
# Requires: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (see docker/Dockerfile).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== SimInspect-X: Workspace Setup ==="
echo ""

# Source ROS 2
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "ERROR: ROS 2 Jazzy not found at /opt/ros/jazzy/setup.bash"
    echo "Install ROS 2 Jazzy first, or use the provided Dockerfile."
    exit 1
fi

# Install system dependencies via rosdep
echo "[1/2] Installing dependencies (rosdep)..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
echo ""

# Build workspace
echo "[2/2] Building workspace (colcon)..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo
echo ""

echo "=== Setup complete ==="
echo ""
echo "Source the workspace:"
echo "  source install/setup.bash"
echo ""
echo "Run tests:"
echo "  colcon test && colcon test-result"