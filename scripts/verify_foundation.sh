#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash setup.sh
set +u
source install/setup.bash
set -u
colcon test --return-code-on-test-failure
colcon test-result --all --verbose
python3 scripts/check_ground_truth_firewall.py --src src
