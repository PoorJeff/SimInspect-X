#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
set -u
command -v sudo >/dev/null
sudo -n true
test -f /etc/ros/rosdep/sources.list.d/20-default.list
python3 -c 'import yaml, numpy, scipy, cv2, osqp'
gz sim --versions
