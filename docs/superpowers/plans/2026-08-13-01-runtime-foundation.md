# Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a clean Ubuntu 24.04 clone build and test reproducibly in the project Docker image, with a truthful project status and a green Gate A on the exact public commit.

**Architecture:** Keep `setup.sh` as the dependency/build entry point and add one repository-owned verifier used by both the VM and GitHub Actions. Replace the grep firewall with a small XML parser, fix only proven container and CMake blockers, and preserve the non-root product runtime while making the CI write policy explicit.

**Tech Stack:** Ubuntu 24.04, Docker, ROS 2 Jazzy, Gazebo Harmonic, rosdep, colcon, Bash, Python 3, pytest, GitHub Actions.

## Global Constraints

- Ground-truth simulator state is allowed for benchmarking only and must never become an input to an autonomous production package.
- Docker builds use repository-root context; the concrete Gate A command is `docker build -f docker/Dockerfile -t siminspect-x:gate-a .`.
- Gate A requires `colcon build --symlink-install`, `colcon test --return-code-on-test-failure`, and `colcon test-result --all --verbose` with zero failures.
- The accepted runtime is Ubuntu 24.04 with ROS 2 Jazzy and Gazebo Harmonic.
- The VM obtains code with `git clone`; VMware shared folders are not part of the supported workflow.
- Keep public status as `implementation complete; runtime validation in progress` until Gates A-E pass on one public commit.
- Do not fabricate a pass when stderr is unavailable; preserve the original failing command and logs.

---

## File Structure

- `.dockerignore` — keeps Git history, build products, raw data, and large generated assets out of the Docker context.
- `scripts/check_ground_truth_firewall.py` — XML-aware L1 dependency firewall CLI.
- `scripts/verify_container_contract.sh` — checks the immutable image contract before a workspace build.
- `scripts/verify_foundation.sh` — the single setup/build/test/firewall sequence used locally and in CI.
- `src/siminspect_benchmark/test/test_foundation_contract.py` — static contracts for CMake install paths, Docker context, and CI delegation.
- `src/siminspect_benchmark/test/test_ground_truth_firewall.py` — parser fixtures and repository firewall tests.
- `docker/Dockerfile`, `setup.sh`, `.github/workflows/ci.yml`, and two package `CMakeLists.txt` files — minimal repairs to satisfy those contracts.

### Task 1: Capture the failing baseline and correct status wording

**Files:**
- Create after execution: `artifacts/validation/gate-a-baseline/commands.txt`
- Create after execution: `artifacts/validation/gate-a-baseline/docker-build.log`
- Create after execution: `artifacts/validation/gate-a-baseline/colcon-build.log`
- Modify: `.agent/PROJECT_STATE.md`
- Modify: `.opencode-memory/OPEN_ISSUES.md`

**Interfaces:**
- Consumes: current commit from `git rev-parse HEAD` and the current Docker/CI commands.
- Produces: an unedited failure transcript and project wording that does not claim runtime acceptance.

- [ ] **Step 1: Record the exact baseline command before changing runtime files**

```bash
mkdir -p artifacts/validation/gate-a-baseline
git rev-parse HEAD | tee artifacts/validation/gate-a-baseline/commit.txt
docker build --pull --progress=plain -f docker/Dockerfile -t siminspect-x:baseline . \
  2>&1 | tee artifacts/validation/gate-a-baseline/docker-build.log
docker run --rm --user root -e DISPLAY= \
  -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:baseline bash -lc '
    set -euxo pipefail
    source /opt/ros/jazzy/setup.bash
    rosdep update
    rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo
  ' 2>&1 | tee artifacts/validation/gate-a-baseline/colcon-build.log
```

Expected: at least the current failure remains visible in a log; this step is evidence capture and may exit non-zero.

- [ ] **Step 2: Replace contradictory completion wording**

Use this exact status sentence in both state files:

```markdown
**Status:** implementation complete; runtime validation in progress
```

List Gate A as blocked by the captured failing command; do not change previously accepted implementation tasks to rejected.

- [ ] **Step 3: Verify only status/evidence files changed**

Run: `git diff -- .agent/PROJECT_STATE.md .opencode-memory/OPEN_ISSUES.md`

Expected: no sentence says `PROJECT_COMPLETE`, runtime-validated, or Gate A passed.

- [ ] **Step 4: Commit the truthful state update**

```bash
git add .agent/PROJECT_STATE.md .opencode-memory/OPEN_ISSUES.md
git commit -m "docs: mark runtime validation in progress"
```

Do not add `artifacts/validation/gate-a-baseline/`; runtime evidence remains ignored and is later packaged for the release.

### Task 2: Lock the package-install and Docker-context contracts

**Files:**
- Create: `.dockerignore`
- Create: `src/siminspect_benchmark/test/test_foundation_contract.py`
- Modify: `src/siminspect_assets/CMakeLists.txt`
- Modify: `src/siminspect_description/CMakeLists.txt`
- Modify: `run_demo.sh`

**Interfaces:**
- Consumes: root-context Docker command and all `install(DIRECTORY ...)` declarations.
- Produces: `test_all_cmake_install_directories_exist()` and `test_all_docker_builds_use_root_context()`.

- [ ] **Step 1: Write the failing structural tests**

```python
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]


def test_all_cmake_install_directories_exist():
    for cmake in ROOT.glob("src/*/CMakeLists.txt"):
        text = cmake.read_text(encoding="utf-8")
        for body in re.findall(r"install\(DIRECTORY\s+([^\)]+?)\s+DESTINATION", text, re.S):
            for name in body.split():
                assert (cmake.parent / name).is_dir(), f"{cmake}: missing {name}"


def test_all_docker_builds_use_root_context():
    demo = (ROOT / "run_demo.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "docker build" in demo
    assert "docker/" not in re.search(r"docker build[^\n]+", demo).group(0).split()[-1]
    assert "context: ." in workflow
    assert "file: docker/Dockerfile" in workflow
```

- [ ] **Step 2: Run the tests and confirm the missing directories are named**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_foundation_contract.py -vv`

Expected: FAIL naming `siminspect_assets/config`, `siminspect_assets/launch`, `siminspect_description/meshes`, or `siminspect_description/config`, and the old demo Docker context.

- [ ] **Step 3: Make the smallest CMake and demo fixes**

Use these install declarations:

```cmake
# src/siminspect_assets/CMakeLists.txt
install(DIRECTORY assets DESTINATION share/${PROJECT_NAME})

# src/siminspect_description/CMakeLists.txt
install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME})
```

Use this build form in `run_demo.sh`:

```bash
docker build -f docker/Dockerfile -t "$IMAGE_NAME" .
```

Create `.dockerignore` with:

```text
.git
.agent
.opencode
.opencode-memory
build
install
log
artifacts
experiments/raw
datasets/gauge_synthetic
__pycache__
*.pyc
*.mp4
```

- [ ] **Step 4: Run the structural tests again**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_foundation_contract.py -vv`

Expected: PASS.

- [ ] **Step 5: Commit the package and context contract**

```bash
git add .dockerignore run_demo.sh \
  src/siminspect_assets/CMakeLists.txt \
  src/siminspect_description/CMakeLists.txt \
  src/siminspect_benchmark/test/test_foundation_contract.py
git commit -m "fix: align package install and docker context"
```

### Task 3: Repair the Docker bootstrap contract

**Files:**
- Create: `scripts/verify_container_contract.sh`
- Modify: `docker/Dockerfile`
- Modify: `setup.sh`
- Test: `src/siminspect_benchmark/test/test_foundation_contract.py`

**Interfaces:**
- Consumes: `/opt/ros/jazzy/setup.bash` and the image's Python/rosdep installation.
- Produces: a non-root image user that can run `sudo -n`, a preinitialized rosdep source list, and a zero-argument verifier.

- [ ] **Step 1: Add the failing image-contract assertions**

Append:

```python
def test_dockerfile_initializes_required_runtime_tools():
    text = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"\bsudo\b", text)
    assert "rosdep init" in text
    assert "USER siminspect" in text
```

Run: `python3 -m pytest src/siminspect_benchmark/test/test_foundation_contract.py -k dockerfile -vv`

Expected: FAIL because `sudo` is not installed and rosdep is not initialized.

- [ ] **Step 2: Create the executable container verifier**

```bash
#!/usr/bin/env bash
set -euo pipefail
source /opt/ros/jazzy/setup.bash
command -v sudo >/dev/null
sudo -n true
test -f /etc/ros/rosdep/sources.list.d/20-default.list
python3 -c 'import yaml, numpy, scipy, cv2, osqp'
gz sim --versions
```

Save it as `scripts/verify_container_contract.sh` and run `chmod +x scripts/verify_container_contract.sh` in Ubuntu.

- [ ] **Step 3: Initialize rosdep before switching users**

Add `sudo` to the Docker apt package list, then add this before `USER siminspect`:

```dockerfile
RUN rosdep init
```

Keep `USER siminspect` and `WORKDIR /home/siminspect`; do not convert the product image to a root runtime.

- [ ] **Step 4: Make setup reuse the initialized state without hiding failures**

Keep the existing guarded initialization and use:

```bash
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo -n rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
```

- [ ] **Step 5: Build and execute the contract in the target image**

```bash
docker build --no-cache --progress=plain -f docker/Dockerfile -t siminspect-x:gate-a .
docker run --rm -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:gate-a bash -lc './scripts/verify_container_contract.sh'
```

Expected: exit 0, an OSQP import, and Gazebo Harmonic version output.

- [ ] **Step 6: Commit the bootstrap repair**

```bash
git add docker/Dockerfile setup.sh scripts/verify_container_contract.sh \
  src/siminspect_benchmark/test/test_foundation_contract.py
git commit -m "fix: make container bootstrap reproducible"
```

### Task 4: Replace the grep firewall with an XML-aware checker

**Files:**
- Create: `scripts/check_ground_truth_firewall.py`
- Create: `src/siminspect_benchmark/test/test_ground_truth_firewall.py`

**Interfaces:**
- Produces: `find_violations(src_root: Path) -> list[str]` and CLI `python3 scripts/check_ground_truth_firewall.py --src src`.
- Exit contract: zero with no dependency violation; one after printing each offending package and dependency tag.

- [ ] **Step 1: Write fixture tests for all ROS dependency tag forms**

```python
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "firewall", ROOT / "scripts/check_ground_truth_firewall.py"
)


def test_exec_depend_is_a_violation(tmp_path):
    package = tmp_path / "siminspect_bad"
    package.mkdir()
    (package / "package.xml").write_text(
        "<package><name>siminspect_bad</name>"
        "<exec_depend>siminspect_benchmark</exec_depend></package>",
        encoding="utf-8",
    )
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(tmp_path) == [
        "siminspect_bad: exec_depend -> siminspect_benchmark"
    ]


def test_repository_has_no_ground_truth_dependency():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    assert module.find_violations(ROOT / "src") == []
```

- [ ] **Step 2: Confirm the parser module is absent**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_ground_truth_firewall.py -vv`

Expected: FAIL while importing `scripts/check_ground_truth_firewall.py`.

- [ ] **Step 3: Implement the focused XML parser**

```python
#!/usr/bin/env python3
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def find_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    for manifest in sorted(src_root.glob("siminspect_*/package.xml")):
        root = ET.parse(manifest).getroot()
        package = (root.findtext("name") or manifest.parent.name).strip()
        if package == "siminspect_benchmark":
            continue
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            value = (element.text or "").strip()
            if (tag == "depend" or tag.endswith("_depend")) and value == "siminspect_benchmark":
                violations.append(f"{package}: {tag} -> {value}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path("src"))
    args = parser.parse_args()
    violations = find_violations(args.src)
    for violation in violations:
        print(f"VIOLATION: {violation}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run unit and repository checks**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_ground_truth_firewall.py -vv
python3 scripts/check_ground_truth_firewall.py --src src
```

Expected: both exit 0.

- [ ] **Step 5: Commit the firewall**

```bash
git add scripts/check_ground_truth_firewall.py \
  src/siminspect_benchmark/test/test_ground_truth_firewall.py
git commit -m "test: enforce ground truth dependency firewall"
```

### Task 5: Create one strict foundation verifier

**Files:**
- Create: `scripts/verify_foundation.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `src/siminspect_benchmark/CMakeLists.txt`
- Test: `src/siminspect_benchmark/test/test_foundation_contract.py`

**Interfaces:**
- Consumes: `setup.sh`, installed workspace, and `check_ground_truth_firewall.py`.
- Produces: `./scripts/verify_foundation.sh`, a zero-argument acceptance command shared by CI and the VM.

- [ ] **Step 1: Register all foundation tests and assert CI delegates**

Append to the structural test:

```python
def test_ci_delegates_to_shared_verifier():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "./scripts/verify_foundation.sh" in workflow
    assert "colcon test --return-code-on-test-failure" not in workflow
```

Register both new test files in `src/siminspect_benchmark/CMakeLists.txt`:

```cmake
ament_add_pytest_test(test_foundation_contract test/test_foundation_contract.py)
ament_add_pytest_test(test_ground_truth_firewall test/test_ground_truth_firewall.py)
```

- [ ] **Step 2: Confirm CI still duplicates the pipeline**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_foundation_contract.py -k ci_delegates -vv`

Expected: FAIL.

- [ ] **Step 3: Create the strict shared verifier**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
bash setup.sh
source install/setup.bash
colcon test --return-code-on-test-failure
colcon test-result --all --verbose
python3 scripts/check_ground_truth_firewall.py --src src
```

Save as `scripts/verify_foundation.sh` and make it executable in Ubuntu.

- [ ] **Step 4: Replace the inline CI pipeline**

The workflow's container command must be:

```yaml
- name: Build and test (headless)
  run: |
    docker run --rm --user root \
      -e DISPLAY= \
      -v "${{ github.workspace }}:/home/siminspect/ws" \
      -w /home/siminspect/ws \
      siminspect-x:ci \
      bash -lc './scripts/verify_foundation.sh'
```

Run the firewall as an earlier host step and upload test evidence even when the container step fails:

```yaml
- name: Ground-truth firewall
  run: python3 scripts/check_ground_truth_firewall.py --src src

- name: Upload test diagnostics
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: colcon-test-diagnostics
    path: |
      log/**
      build/**/test_results/**
```

Set `timeout-minutes: 60` on the job.

- [ ] **Step 5: Run shell syntax and structural tests**

```bash
bash -n setup.sh
bash -n scripts/verify_container_contract.sh
bash -n scripts/verify_foundation.sh
python3 -m pytest src/siminspect_benchmark/test/test_foundation_contract.py -vv
```

Expected: all pass.

- [ ] **Step 6: Execute the complete verifier inside the image**

```bash
docker run --rm --user root -e DISPLAY= \
  -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:gate-a bash -lc './scripts/verify_foundation.sh'
```

Expected: build succeeds, tests return zero, `colcon test-result` reports zero failures, firewall exits zero.

- [ ] **Step 7: Commit the shared verifier and CI wiring**

```bash
git add scripts/verify_foundation.sh .github/workflows/ci.yml \
  src/siminspect_benchmark/CMakeLists.txt \
  src/siminspect_benchmark/test/test_foundation_contract.py
git commit -m "ci: share the strict foundation verifier"
```

### Task 6: Prove Gate A in a clean VMware clone

**Files:**
- Create after execution: `artifacts/validation/$RUN_ID/gate-a/environment.txt`
- Create after execution: `artifacts/validation/$RUN_ID/gate-a/verify-foundation.log`
- Modify after PASS: `.agent/PROJECT_STATE.md`
- Modify after PASS: `.opencode-memory/OPEN_ISSUES.md`

**Interfaces:**
- Consumes: a pushed exact commit and a NAT-connected Ubuntu 24.04 VMware guest.
- Produces: Gate A evidence bound to one commit; it does not imply Gates B-E passed.

- [ ] **Step 1: Push the implementation commit and clone it independently in the VM**

```bash
git push origin main
VM_USER="${SIMINSPECT_VM_USER:?export SIMINSPECT_VM_USER with the Ubuntu account name}"
VM_HOST="${SIMINSPECT_VM_HOST:-192.168.101.151}"
ssh "$VM_USER@$VM_HOST" '
  GATE_CLONE="$HOME/workspace/SimInspect-X-gate-a-$(date -u +%Y%m%dT%H%M%SZ)"
  git clone https://github.com/PoorJeff/SimInspect-X.git \
    "$GATE_CLONE"
  cd "$GATE_CLONE"
  test -z "$(git status --porcelain)"
  git rev-parse HEAD
  printf "GATE_CLONE=%s\n" "$GATE_CLONE"
'
```

Set `SIMINSPECT_VM_USER` from the configured Ubuntu account name discovered from the VM console or SSH configuration; do not guess credentials or enable a shared folder. Continue the remaining steps from the printed `GATE_CLONE` path.

- [ ] **Step 2: Capture the target environment**

In the VM clone:

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)_$(git rev-parse --short HEAD)_gate-a"
EVIDENCE="$HOME/siminspect-evidence/$RUN_ID/gate-a"
mkdir -p "$EVIDENCE"
{
  git rev-parse HEAD
  lsb_release -ds
  uname -a
  nproc
  free -h
  df -h /
  docker version
} | tee "$EVIDENCE/environment.txt"
```

- [ ] **Step 3: Build and execute Gate A from the clean clone**

```bash
docker build --pull --progress=plain -f docker/Dockerfile -t siminspect-x:gate-a . \
  2>&1 | tee "$EVIDENCE/docker-build.log"
docker run --rm --user root -e DISPLAY= \
  -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:gate-a bash -lc './scripts/verify_container_contract.sh && ./scripts/verify_foundation.sh' \
  2>&1 | tee "$EVIDENCE/verify-foundation.log"
```

Expected: every command exits zero and the repository remains clean.

- [ ] **Step 4: Verify the exact public commit's Actions run**

```bash
git rev-parse HEAD
git status --porcelain
```

Open the Actions run for that SHA and require the Docker build, firewall, shared verifier, and diagnostic-upload steps to complete successfully. If it fails, preserve the run URL and stderr, create a new fix commit, and repeat Task 6 from a new clean clone.

- [ ] **Step 5: Mark only Gate A as passed**

Update the state/open-issue files with the SHA, VM run ID, and Actions URL. Keep the overall wording `runtime validation in progress`.

- [ ] **Step 6: Commit Gate A evidence references**

```bash
git add .agent/PROJECT_STATE.md .opencode-memory/OPEN_ISSUES.md
git commit -m "docs: record reproducible foundation evidence"
```

## Plan Acceptance

Run in the clean VM clone:

```bash
docker build --pull -f docker/Dockerfile -t siminspect-x:gate-a .
docker run --rm --user root -e DISPLAY= \
  -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:gate-a bash -lc './scripts/verify_container_contract.sh && ./scripts/verify_foundation.sh'
test -z "$(git status --porcelain)"
```

Accept this plan only when the exact pushed SHA is clean in the VM, all commands above pass, and the same SHA has a green GitHub Actions run. Do not advance to formal runtime evidence if Gate A is red.
