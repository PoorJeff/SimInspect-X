#!/usr/bin/env bash
# Save the SLAM map to file. Run while SLAM is active.
set -euo pipefail
MAP_DIR="${1:-$HOME/maps}"
MAP_NAME="${2:-siminspect_plant}"
mkdir -p "$MAP_DIR"
ros2 run nav2_map_server map_saver_cli -f "$MAP_DIR/$MAP_NAME"
echo "Map saved to $MAP_DIR/$MAP_NAME"
