#!/usr/bin/env bash
# SimInspect-X one-command demo. Docker is a transport; the Python
# orchestrator owns one evidence-backed run and every cleanup path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="siminspect-x"

usage() {
    cat <<'EOF'
Usage:
  ./run_demo.sh --headless              # CPU/headless public demo
  ./run_demo.sh --visual                # visual Gazebo + RViz demo
  ./run_demo.sh --visual --record       # visual demo with live evidence media

Benchmark/reproducibility overrides:
  --method B0|P2 --scenario F00|F06|F07 --seed 1-10|21-25
  --artifact-root PATH --benchmark-evidence

Host-only:
  --build                               # rebuild the repository-root image
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

IN_DOCKER=0
FORCE_BUILD=0
FORWARDED=()
for arg in "$@"; do
    case "$arg" in
        --in-docker) IN_DOCKER=1 ;;
        --build) FORCE_BUILD=1 ;;
        *) FORWARDED+=("$arg") ;;
    esac
done

if [[ "$IN_DOCKER" == "1" ]]; then
    cd "$SCRIPT_DIR"
    set +u
    source /opt/ros/jazzy/setup.bash
    if [[ -f install/setup.bash ]]; then
        source install/setup.bash
    else
        echo "[container] workspace not built; running setup.sh"
        bash setup.sh
        source install/setup.bash
    fi
    set -u
    exec python3 -m siminspect_bringup.demo_orchestrator "${FORWARDED[@]}"
fi

cd "$SCRIPT_DIR"
if [[ "$FORCE_BUILD" == "1" ]] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "[host] building $IMAGE_NAME from repository root"
    docker build -f docker/Dockerfile -t "$IMAGE_NAME" .
fi

# Deliberately omit -t: headless runs must work without a TTY in VMware/CI.
exec docker run --rm --init --shm-size=2g -i \
    -v "$SCRIPT_DIR:/workspace" -w /workspace \
    "$IMAGE_NAME" bash /workspace/run_demo.sh --in-docker "${FORWARDED[@]}"
