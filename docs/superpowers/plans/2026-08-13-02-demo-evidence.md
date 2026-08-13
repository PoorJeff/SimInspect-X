# Demo Runtime and Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one real, bounded, evidence-producing SimInspect-X demo that runs the same autonomy graph in headless, visual, and recorded modes and passes product Gates B and C.

**Architecture:** `siminspect_bringup` owns validated configuration, the component graph, readiness probes, process supervision, immutable run artifacts, and acceptance evaluation. Mission execution remains the only Nav2 and precision-control dispatcher; asset, viewpoint, vision, fault, and mission nodes exchange explicit current-asset/attempt state. `run_demo.sh` is only a Docker/CLI shim over the Python orchestrator.

**Tech Stack:** Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, Nav2, SLAM Toolbox, `robot_localization`, `rclpy`, Python 3, PyYAML, OpenCV, OSQP, pytest, Bash, Docker, FFmpeg.

## Global Constraints

- Preserve the approved project thesis; this plan closes runtime, demo, and evidence gaps only.
- Simulator ground truth and hidden gauge values remain benchmark-only inputs.
- Visual and headless modes use one orchestrator, component graph, configuration, mission, and acceptance evaluator.
- The three documented public invocations are `./run_demo.sh --headless`, `./run_demo.sh --visual`, and `./run_demo.sh --visual --record`; benchmark overrides `--method`, `--scenario`, `--seed`, and `--artifact-root` are supported but remain in the reproducibility documentation rather than the README quick-start block.
- Development/demo seeds are 21-25; this plan uses seed 21 for F00 and seed 21 with explicit override for F06/F07 smoke runs.
- Every run ID follows `YYYYMMDDTHHMMSSZ_$SHORT_COMMIT_$MODE_$SEED` and an existing run directory is never overwritten.
- Failed runs, failed assets, partial reports, logs, and events remain on disk.
- Readiness and mission waits are bounded; fixed sleeps never prove readiness.
- `SIGINT`, `SIGTERM`, readiness failure, mission timeout, and normal completion share one owned-process cleanup path.
- Standard demo runs keep the production graph free of benchmark truth; `--benchmark-evidence` is an internal flag used by Plan 03 to add only the benchmark publisher/recorder and `benchmark_evaluation.json` without changing autonomy.
- A successful run requires every expected asset to have a result or explicit bounded failure, at least one camera-pipeline reading, a verified return home, a valid report, and zero owned processes after cleanup.
- F06 must physically block the configured fixed viewpoint. F07 must alter camera frames consumed by the reader and deterministically cause an alternate-viewpoint attempt.
- No public evidence is accepted from a dirty worktree or a different commit than `manifest.json.git.commit_sha`.

---

## File Map and Locked Contracts

Create `src/siminspect_bringup` as an `ament_cmake_python` package. `demo_config.py` validates configuration; `component_graph.py` returns process specifications; `run_artifacts.py` owns atomic files and events; `readiness.py` implements probes; `process_supervisor.py` owns POSIX process groups; `acceptance.py` validates a run; `demo_orchestrator.py` composes them. `rviz/demo.rviz` is the only visual-only autonomy-neutral configuration.

Locked Python contracts:

```python
@dataclass(frozen=True)
class DemoConfig:
    world: Path
    mission_assets: tuple[str, ...]
    ordering: Literal["list", "greedy"]
    method: Literal["B0", "P2"]
    controller: Literal["pid", "mpc"]
    scenario: Literal["F00", "F06", "F07"]
    seed: int
    readiness_timeout_s: float
    mission_timeout_s: float

def load_demo_config(path: Path) -> DemoConfig: ...
def build_component_graph(config: DemoConfig, mode: str, record: bool,
                          benchmark_evidence: bool,
                          run_dir: Path) -> tuple[ProcessSpec, ...]: ...
def build_run_id(started_at: datetime, commit_sha: str,
                 mode: Literal["headless", "visual"], seed: int) -> str: ...
def validate_mission_report(report: Mapping[str, object],
                            expected_assets: Sequence[str],
                            run_id: str) -> list[GateResult]: ...
```

`acceptance.json` is `{schema_version:"1.0",run_id,overall:"passed"|"failed",gates:[{id,status:"passed"|"failed",reason,evidence:[relative paths]}]}`. `manifest.json.git` contains `commit_sha`, `short_commit`, and `dirty`. `events.jsonl` lines contain `schema_version`, RFC3339 UTC `timestamp`, `monotonic_s`, `run_id`, `event`, `component`, `status`, and `details`.

Formal event names are `mission.started`, `navigation.started`, `navigation.completed`, `viewpoint.selected`, `precision.started`, `precision.completed`, `gauge.reading`, `reinspection.requested`, `reinspection.viewpoint_selected`, `mission.return_home_started`, `mission.return_home.completed`, `mission.report_written`, and `run.acceptance_completed`.

Every viewpoint event's `details` contains `asset_id`, `request_id`, `candidate_index`, `pose`, `method`, and `attempt`. Plan 03 uses the same CLI with `--method B0` and `--method P2`; the method changes only the selector process, never the mission, navigation, precision, vision, fault, or acceptance components.

Media paths are `media/demo.mp4` and `media/screenshots/01-navigation.webp` through `05-mission-complete.webp`. `media/index.json` is `{schema_version:"1.0",run_id,items:[{kind,path,sha256,source:"live_capture",started_at,ended_at,width_px,height_px,fps}]}` with paths relative to the run directory.

When the CLI is invoked with `--benchmark-evidence`, the component graph also starts the existing `siminspect_benchmark` ground-truth publisher plus a benchmark-owned evaluation recorder. The recorder alone subscribes to `/benchmark_ground_truth/robot_pose`, gauge-reading outputs, fault-state evidence, and mission events, then writes `benchmark_evaluation.json` beside the report after mission completion. Its contract is `{schema_version:"1.0",run_id,producer:"siminspect_benchmark",valid_read_count,reading_count,absolute_errors,path_length_m,alternative_viewpoint_attempts,distinct_viewpoints_by_asset,recovery_count,f06_occluder_spawned,f06_occluder_model,f07_camera_frames_modified}`. Production packages never read this file or its input topics. `robot_spawn.launch.py` receives `publish_ground_truth:=false` by default; benchmark mode starts the publisher from the bringup graph so a standard demo has no benchmark process.

### Task 1: Repair the mission/viewpoint/vision control contract

**Files:**
- Modify: `src/siminspect_interfaces/msg/MissionState.msg:1-5`
- Modify: `src/siminspect_mission/siminspect_mission/mission_executor.py:215-552`
- Modify: `src/siminspect_mission/siminspect_mission/report_schema.py:13-87`
- Modify: `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p2_selector.py:15-138`
- Modify: `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/b0_selector.py:1-45`
- Modify: `src/siminspect_gauge_vision/siminspect_gauge_vision/gauge_vision_node.py:20-45`
- Modify: `src/siminspect_precision_control/launch/precision_approach.launch.py:7-37`
- Test: `src/siminspect_mission/test/test_mission_executor.py`
- Test: `src/siminspect_mission/test/test_report_writer.py`
- Test: `src/siminspect_viewpoint_planner/test/test_p2_selector.py`
- Create: `src/siminspect_gauge_vision/test/test_gauge_vision_node_contract.py`

**Interfaces:**
- Consumes: existing `/inspection/assets`, `/inspection/gauge_reading`, `/odometry/filtered`, `navigate_to_pose`, and `precision_approach`.
- Produces: `MissionState` fields `state`, `current_asset_id`, `attempt`, `viewpoint_index`, `request_id`, and `timestamp`; B0 or P2 publishes one selected viewpoint per matching request; mission parameters `run_id`, `report_path`, `expected_asset_ids`, and per-state deadlines.

- [ ] **Step 1: Write failing contract tests**

Add tests proving duplicate `AssetArray` messages do not reset `asset_idx`; a reading with the wrong asset ID is ignored; entering `SELECT_VIEWPOINT` increments `request_id`; B0 and P2 each publish exactly once for `(asset_id, request_id)`; P2 blacklists the previous candidate after low confidence; Vision publishes only while state is `INSPECT`; rejected or aborted return-home goals do not emit `HOME_REACHED`; missing odom, viewpoint, and reading expire into bounded failure records; report includes the supplied `run_id` and writes to `report_path`.

- [ ] **Step 2: Run tests and observe the current wiring failures**

Run:

```bash
python3 -m pytest \
  src/siminspect_mission/test/test_mission_executor.py \
  src/siminspect_mission/test/test_report_writer.py \
  src/siminspect_viewpoint_planner/test/test_p2_selector.py \
  src/siminspect_gauge_vision/test/test_gauge_vision_node_contract.py -q
```

Expected: FAIL because `request_id`, explicit report parameters, asset filtering, state-gated vision, and strict return-home behavior do not exist.

- [ ] **Step 3: Implement the single-dispatch mission contract**

Make Mission ignore duplicate asset inventories after the first validated load. Publish the current asset and a monotonically increasing `request_id` whenever a viewpoint is required. Make B0 and P2 cache assets but select only for the current request; on a later request for the same asset, P2 excludes previously published candidate indices while B0 deliberately republishes its fixed pose. Make Mission reject readings whose `asset_id` does not match its current asset. Gate Vision on `MissionState.state == "INSPECT"` and a non-empty asset ID. Remove `handoff_manager` from the production launch graph so Mission is the only PrecisionApproach client. Replace return-home degradation with checked goal acceptance, checked `GoalStatus.STATUS_SUCCEEDED`, and final odometry distance `<= 0.10 m`. Add bounded state deadlines that record `timeout` rather than waiting forever.

- [ ] **Step 4: Run the focused tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/siminspect_interfaces src/siminspect_mission src/siminspect_viewpoint_planner src/siminspect_gauge_vision src/siminspect_precision_control/launch/precision_approach.launch.py
git commit -m "fix: close demo mission wiring"
```

### Task 2: Make the simulated gauges visible and installable

**Files:**
- Create: `src/siminspect_sim/models/gauge_asset/model.config`
- Create: `src/siminspect_sim/models/gauge_asset/model.sdf`
- Create: `src/siminspect_sim/models/gauge_asset/materials/textures/gauge_face.png`
- Modify: `src/siminspect_sim/worlds/plant.sdf:46-76`
- Modify: `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/candidate_generator.py:1-58`
- Modify: `src/siminspect_viewpoint_planner/siminspect_viewpoint_planner/p2_selector.py:1-31`
- Test: `src/siminspect_sim/test/test_world_assets.py`
- Create: `src/siminspect_viewpoint_planner/test/test_installed_imports.py`

**Interfaces:**
- Consumes: six poses in `src/siminspect_assets/assets/*.yaml` and the blue-needle detector contract.
- Produces: six named, camera-visible gauge models whose face pose matches the registry; package-qualified imports that work from `install/`.

- [ ] **Step 1: Write failing world/import tests**

Assert `plant.sdf` includes exactly the six registry IDs, each pose equals its YAML pose within `1e-3`, and `gauge_face.png` yields confidence `>= 0.80` through `run_pipeline()`. Add an installed-space subprocess test importing `siminspect_viewpoint_planner.candidate_generator` and `.p2_selector` without modifying `sys.path`.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_sim/test/test_world_assets.py src/siminspect_viewpoint_planner/test/test_installed_imports.py -q
```

Expected: FAIL because the world contains no gauge models and planner modules use top-level imports.

- [ ] **Step 3: Implement the minimal gauge model and qualified imports**

Build one reusable circular face with a blue needle, instantiate it six times at the registry poses, and use package-qualified imports with the existing local fallback only for source-tree unit tests. Do not encode or publish the hidden value to production nodes.

- [ ] **Step 4: Verify source and installed behavior**

```bash
python3 -m pytest src/siminspect_sim/test/test_world_assets.py src/siminspect_viewpoint_planner/test/test_installed_imports.py -q
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select siminspect_sim siminspect_viewpoint_planner
source install/setup.bash
python3 -c "import siminspect_viewpoint_planner.candidate_generator, siminspect_viewpoint_planner.p2_selector"
```

Expected: all commands PASS.

- [ ] **Step 5: Commit**

```bash
git add src/siminspect_sim src/siminspect_viewpoint_planner
git commit -m "feat: add inspectable gauge world assets"
```

### Task 3: Add validated configuration and one component graph

**Files:**
- Create: `src/siminspect_bringup/CMakeLists.txt`
- Create: `src/siminspect_bringup/package.xml`
- Create: `src/siminspect_bringup/siminspect_bringup/__init__.py`
- Create: `src/siminspect_bringup/siminspect_bringup/demo_config.py`
- Create: `src/siminspect_bringup/siminspect_bringup/component_graph.py`
- Modify: `config/demo_config.yaml:1-20`
- Modify: `src/siminspect_description/launch/robot_spawn.launch.py:1-48`
- Modify: `src/siminspect_description/urdf/siminspect.gazebo.xacro:1-112`
- Create: `src/siminspect_bringup/test/test_demo_config.py`
- Create: `src/siminspect_bringup/test/test_component_graph.py`

**Interfaces:**
- Consumes: locked `DemoConfig` contract and executable names from Tasks 1-2.
- Produces: `load_demo_config(Path) -> DemoConfig` and `build_component_graph(...) -> tuple[ProcessSpec, ...]`.

- [ ] **Step 1: Write failing config/graph tests**

Test invalid mode, seed outside both the development pool 21-25 and the final pool 1-10, fewer than five or duplicate assets, unknown method/scenario/controller, non-existent world, and `record=True` with headless mode. Assert headless and visual graphs have byte-identical autonomy process specs; visual adds only Gazebo GUI, RViz, and optional recorder. Assert method, scenario, seed, controller, run ID/report path, and all six assets appear in node arguments. Assert B0 and P2 graphs differ only in the selector process. Assert `robot_spawn.launch.py` defaults `publish_ground_truth` to false and benchmark mode alone adds the benchmark publisher/recorder. Replace the invalid `/model/siminspect_amr/pose@nav_msgs/msg/Odometry@gz.msgs.Pose` bridge with a Gazebo PosePublisher configured for `use_pose_vector_msg=true` plus a one-way `tf2_msgs/msg/TFMessage` bridge; make the benchmark publisher extract only the `siminspect_amr` transform into `/benchmark_ground_truth/robot_pose`. Direct public demo use defaults to seed 21; Plan 03 may pass final seeds 1-10 through the same validated path.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_bringup/test/test_demo_config.py src/siminspect_bringup/test/test_component_graph.py -q
```

Expected: FAIL because the package and APIs do not exist.

- [ ] **Step 3: Implement config and graph**

Use frozen dataclasses, reject unknown YAML keys, resolve repository-relative paths after validation, and create explicit `ProcessSpec(name, argv, log_path, env)` instances. Start EKF only once. Use SLAM mapping consistently for this demo rather than simultaneously launching localization with a missing saved map.

- [ ] **Step 4: Verify tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/demo_config.yaml src/siminspect_bringup
git commit -m "feat: define unified demo component graph"
```

### Task 4: Implement immutable artifacts and acceptance schemas

**Files:**
- Create: `src/siminspect_bringup/siminspect_bringup/run_artifacts.py`
- Create: `src/siminspect_bringup/siminspect_bringup/acceptance.py`
- Create: `src/siminspect_bringup/test/test_run_artifacts.py`
- Create: `src/siminspect_bringup/test/test_acceptance.py`
- Modify: `.gitignore:1-13`

**Interfaces:**
- Consumes: locked schemas above and Mission report schema v1.1 from Task 1.
- Produces: `RunArtifacts.create(...)`, `append_event(...)`, `write_json_atomic(...)`, `finalize_manifest(...)`, `validate_mission_report(...)`, and `evaluate_run(...)`.

- [ ] **Step 1: Write failing artifact/acceptance tests**

Test run-ID regex; refusal to reuse a directory; atomic JSON writes; relative evidence paths; one-line valid JSON events; failed-run preservation; SHA-256 verification; manifest exclusion from its own checksum set; exact six-asset semantics; at least one successful camera reading; bounded attempts; strict return-home evidence; and overall failure if any required gate fails.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_bringup/test/test_run_artifacts.py src/siminspect_bringup/test/test_acceptance.py -q
```

Expected: FAIL because artifact and evaluator APIs do not exist.

- [ ] **Step 3: Implement immutable run output**

Create the approved directory layout, copy validated config, record full commit SHA/dirty state/container image/ROS/Gazebo versions, stream events with wall and monotonic time, and finalize checksums only after logs/media/report/acceptance exist. Write JSON through same-directory temporary files followed by `os.replace`.

- [ ] **Step 4: Verify tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore src/siminspect_bringup
git commit -m "feat: preserve immutable demo evidence"
```

### Task 5: Add bounded readiness probes and owned-process cleanup

**Files:**
- Create: `src/siminspect_bringup/siminspect_bringup/readiness.py`
- Create: `src/siminspect_bringup/siminspect_bringup/process_supervisor.py`
- Create: `src/siminspect_bringup/test/test_readiness.py`
- Create: `src/siminspect_bringup/test/test_process_supervisor.py`

**Interfaces:**
- Consumes: `ProcessSpec`, `RunArtifacts.append_event`, ROS graph and action/lifecycle APIs.
- Produces: `ProbeResult(probe_id,status,elapsed_s,reason,observed,evidence)`, `run_readiness_probe(probe, timeout_s)`, `ProcessSupervisor.start(spec)`, `terminate_all(grace_s=10.0)`, and `assert_all_stopped()`.

- [ ] **Step 1: Write failing pure tests**

Use fake probes and parent/child processes to test pass, timeout, early child death, SIGINT, SIGTERM, normal exit, log retention, and cleanup escalation `SIGINT -> SIGTERM -> SIGKILL`. Assert no process group member remains and every failure records component, expected condition, observed condition, timeout, and log path.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_bringup/test/test_readiness.py src/siminspect_bringup/test/test_process_supervisor.py -q
```

Expected: FAIL because probe and supervisor APIs do not exist.

- [ ] **Step 3: Implement probes and supervisor**

Implement ordered bounded probes for `/clock`; robot description and essential TF; minimum-rate `/scan`, `/imu/data`, `/camera/image_raw`, `/wheel/odometry`; `/odometry/filtered`; `map -> base_link`; active Nav2 lifecycle nodes; `navigate_to_pose` and `precision_approach`; and discovery of assets, viewpoint, vision, and mission interfaces. Start every process in a new session and reap it after cleanup.

- [ ] **Step 4: Verify tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/siminspect_bringup
git commit -m "feat: probe readiness and clean demo processes"
```

### Task 6: Wire real F06 and F07 fault actuation

**Files:**
- Create: `src/siminspect_benchmark/models/blocking_box/model.sdf`
- Create: `src/siminspect_benchmark/siminspect_benchmark/fault_image_relay.py`
- Create: `src/siminspect_benchmark/siminspect_benchmark/e4_evidence_recorder.py`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/fault_injector.py:32-126`
- Modify: `src/siminspect_benchmark/config/fault_scenarios.yaml:58-74`
- Modify: `src/siminspect_gauge_vision/siminspect_gauge_vision/gauge_vision_node.py:20-29`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:5-16`
- Modify: `src/siminspect_benchmark/package.xml:11-20`
- Test: `src/siminspect_benchmark/test/test_fault_injector.py`
- Create: `src/siminspect_benchmark/test/test_fault_image_relay.py`
- Create: `src/siminspect_benchmark/test/test_fault_actuation_launch.py`
- Create: `src/siminspect_benchmark/test/test_e4_evidence_recorder.py`

**Interfaces:**
- Consumes: `/camera/image_raw`, `ros_gz_sim spawn_entity`, F06/F07 configuration, and seed.
- Produces: `/camera/image_faulted` for production Vision input; `/benchmark/fault_state` JSON containing scenario, seed, actuator, active, and evidence; Gazebo entity `f06_blocking_box`; benchmark-only `benchmark_evaluation.json` with real path, gauge-error, re-inspection, recovery, and actuator metrics.

- [ ] **Step 1: Write failing actuator tests**

Assert F07 applies `cv2.GaussianBlur(..., sigmaX=3.0)` deterministically, publishes altered frames with preserved headers, and leaves F00 byte-identical. Derive the F06 pose with the same B0 function from `gauge_pump_01` (`x=3.0`, `y=1.8`, `yaw=3.14`, `desired_distance_m=0.8`), assert the result is within `0.01 m` of `(2.20, 1.80)`, and build the exact `ros2 run ros_gz_sim spawn_entity --name f06_blocking_box --sdf_filename BLOCKING_BOX_SDF --pos 2.20 1.80 0.50 --euler 0.0 0.0 0.0` command. Require a successful spawn confirmation and assert the box footprint intersects the B0 goal tolerance while leaving at least one P2 candidate collision-free. Update `fault_scenarios.yaml` from the stale `(4.0, 1.0)` pose to the derived fixed-viewpoint pose. Add a contract test that Vision consumes only `/camera/image_faulted` in demo mode. Test the recorder's Euclidean trajectory accumulation, match readings to benchmark-only asset truth by `asset_id`, count distinct re-inspection poses and recoveries, require `producer == "siminspect_benchmark"`, and reject a run-ID mismatch.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_fault_injector.py src/siminspect_benchmark/test/test_fault_image_relay.py src/siminspect_benchmark/test/test_fault_actuation_launch.py src/siminspect_benchmark/test/test_e4_evidence_recorder.py -q
```

Expected: FAIL because F06 is a stub and F07 never touches camera frames.

- [ ] **Step 3: Implement the two real actuators**

Make F00/F07 use one relay so the consumer topic never changes. For F06, spawn the box only after `/world/plant/create` is bridged and record the response; on cleanup delete the owned entity. Emit structured fault-state messages and evidence events. Do not treat metadata-only publication as successful actuation. The evaluation recorder loads declared benchmark truth from benchmark configuration, never from the Mission report, integrates the benchmark pose trajectory, joins readings by asset ID after the run, atomically writes the locked `benchmark_evaluation.json`, and is started only in benchmark/evidence mode.

- [ ] **Step 4: Verify unit and Gazebo smoke behavior**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_fault_injector.py src/siminspect_benchmark/test/test_fault_image_relay.py src/siminspect_benchmark/test/test_fault_actuation_launch.py src/siminspect_benchmark/test/test_e4_evidence_recorder.py -q
ros2 topic hz /camera/image_raw --window 30
ros2 topic hz /camera/image_faulted --window 30
ros2 topic echo /benchmark/fault_state --once
gz model --list | grep '^f06_blocking_box$'
```

Expected: tests PASS; both image streams publish; state reports the requested active actuator; F06 entity exists only during the run.

- [ ] **Step 5: Commit**

```bash
git add src/siminspect_benchmark src/siminspect_gauge_vision/siminspect_gauge_vision/gauge_vision_node.py
git commit -m "feat: actuate F06 and F07 faults"
```

### Task 7: Implement the orchestrator and public CLI

**Files:**
- Create: `src/siminspect_bringup/siminspect_bringup/demo_orchestrator.py`
- Create: `src/siminspect_bringup/test/test_demo_cli.py`
- Modify: `run_demo.sh:1-160`
- Modify: `docker/Dockerfile:19-71`

**Interfaces:**
- Consumes: Tasks 3-6 contracts.
- Produces: CLI exit code `0` only for accepted runs, printed `RUN_ID=$RUN_ID` and `RUN_DIR=$RUN_DIR`, and one finalized artifact tree on every exit path.

- [ ] **Step 1: Write failing CLI tests**

Test the three documented invocations plus the benchmark overrides `--method B0|P2`, `--scenario F00|F06|F07`, `--seed 1-10|21-25`, `--artifact-root PATH`, and internal `--benchmark-evidence`; reject `--record` without `--visual`, no TTY in headless Docker, repository-root Docker context, `--init`, `--shm-size=2g`, argument forwarding, stale root-level report immunity, non-zero readiness/mission failures, signal cleanup, and finalization of failed runs. Assert the benchmark publisher/recorder are absent without `--benchmark-evidence` and are the only added processes when it is present.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_bringup/test/test_demo_cli.py -q
bash -n run_demo.sh
```

Expected: pytest FAIL because the orchestrator and flags do not exist; Bash syntax passes.

- [ ] **Step 3: Implement orchestration**

Make the shell script build with `docker build -f docker/Dockerfile .` and execute the installed Python module. The orchestrator creates artifacts before launching, installs signal handlers, starts each dependency only after its predecessor probe passes, monitors unexpected exits, waits for the current run's report, evaluates acceptance, cleans all owned processes, writes the final event/manifest, and returns the acceptance result.

- [ ] **Step 4: Verify CLI behavior**

```bash
python3 -m pytest src/siminspect_bringup/test/test_demo_cli.py -q
bash -n run_demo.sh
./run_demo.sh --help
```

Expected: PASS; help leads with the three public invocations and separately labels the four benchmark/reproducibility overrides.

- [ ] **Step 5: Commit**

```bash
git add run_demo.sh docker/Dockerfile src/siminspect_bringup
git commit -m "feat: orchestrate evidence-backed demos"
```

### Task 8: Add visual and live-recording outputs

**Files:**
- Create: `src/siminspect_bringup/rviz/demo.rviz`
- Create: `src/siminspect_bringup/siminspect_bringup/media_capture.py`
- Create: `src/siminspect_bringup/test/test_media_capture.py`
- Modify: `src/siminspect_bringup/CMakeLists.txt`
- Modify: `docker/Dockerfile`

**Interfaces:**
- Consumes: formal events and `RunArtifacts` from Task 4.
- Produces: `media/demo.mp4`, five named screenshots, `media/index.json`, and `media/recording-metadata.json` tied to the same run ID.

- [ ] **Step 1: Write failing media tests**

Use a generated two-second FFmpeg test source and formal event fixture. Assert MP4 probe success, required screenshot names, `source == "live_capture"`, matching run ID, dimensions/fps/timestamps, relative paths, and SHA-256 values. Assert recording never affects autonomy process specs.

- [ ] **Step 2: Verify failure**

```bash
python3 -m pytest src/siminspect_bringup/test/test_media_capture.py -q
```

Expected: FAIL because capture APIs and RViz config do not exist.

- [ ] **Step 3: Implement visual-only processes and capture**

Configure RViz to show TF, map, robot, Nav2 path, candidate markers, and selected viewpoint. Capture the live visual desktop to `media/demo.mp4`; select screenshots from `monotonic_s` values for navigation, viewpoint selection, gauge reading, reinspection, and mission completion. Record capture command, start/end, dimensions, fps, display, commit, and checksums.

- [ ] **Step 4: Verify media outputs**

```bash
python3 -m pytest src/siminspect_bringup/test/test_media_capture.py -q
RECORD_OUTPUT="$(./run_demo.sh --visual --record)"
printf '%s\n' "$RECORD_OUTPUT"
RUN_ID="$(printf '%s\n' "$RECORD_OUTPUT" | sed -n 's/^RUN_ID=//p' | tail -1)"
test -n "$RUN_ID"
RUN_DIR="artifacts/runs/$RUN_ID"
ffprobe "$RUN_DIR/media/demo.mp4"
(cd "$RUN_DIR" && sha256sum --check SHA256SUMS)
```

Expected: tests and probes PASS; all media index paths resolve.

- [ ] **Step 5: Commit**

```bash
git add docker/Dockerfile src/siminspect_bringup
git commit -m "feat: capture live visual demo evidence"
```

### Task 9: Pass Gate B and Gate C on Ubuntu

**Files:**
- Create: `src/siminspect_bringup/test/test_gate_b_runtime.py`
- Create: `src/siminspect_bringup/test/test_gate_c_runtime.py`
- Modify: `src/siminspect_bringup/siminspect_bringup/acceptance.py`
- Modify: `config/demo_config.yaml`

**Interfaces:**
- Consumes: all preceding task contracts.
- Produces: accepted F00 headless run, accepted F07 reinspection run, accepted F06 recovery run, and machine-readable Gate B/C evidence.

- [ ] **Step 1: Add runtime acceptance tests**

Gate B asserts plant loaded, robot/sensor rates, localization and Nav2 readiness, public interfaces exchanging messages, and OSQP MPC returning a non-fallback command. Gate C asserts six assets, six terminal records, at least one valid camera reading, bounded attempts, real alternate viewpoint under F07, strict return home, valid current-run report, zero leaked processes, and accepted checksums.

- [ ] **Step 2: Run the full build/test gate before runtime**

```bash
docker build --progress=plain -f docker/Dockerfile -t siminspect-x:dev .
docker run --rm --init --shm-size=2g -v "$PWD:/home/siminspect/workspace" siminspect-x:dev bash -lc '
  source /opt/ros/jazzy/setup.bash
  cd /home/siminspect/workspace
  colcon build --symlink-install
  colcon test --return-code-on-test-failure
  colcon test-result --all --verbose
'
```

Expected: zero build and test failures before an end-to-end run is accepted.

- [ ] **Step 3: Run and preserve the three development scenarios**

```bash
F00_OUTPUT="$(./run_demo.sh --headless --scenario F00 --seed 21)"
F07_OUTPUT="$(./run_demo.sh --headless --scenario F07 --seed 21)"
F06_OUTPUT="$(./run_demo.sh --headless --scenario F06 --seed 21)"
F00_RUN_ID="$(printf '%s\n' "$F00_OUTPUT" | sed -n 's/^RUN_ID=//p' | tail -1)"
F07_RUN_ID="$(printf '%s\n' "$F07_OUTPUT" | sed -n 's/^RUN_ID=//p' | tail -1)"
F06_RUN_ID="$(printf '%s\n' "$F06_OUTPUT" | sed -n 's/^RUN_ID=//p' | tail -1)"
test -n "$F00_RUN_ID" && test -n "$F07_RUN_ID" && test -n "$F06_RUN_ID"
```

Expected: each prints a distinct run ID and exits `0`; F07 events contain `reinspection.requested` followed by `reinspection.viewpoint_selected` for a different pose; F06 evidence contains successful entity spawn and bounded route/viewpoint recovery.

- [ ] **Step 4: Validate Gate B/C artifacts and cleanup**

In the same shell, validate all three captured run IDs:

```bash
for RUN_ID in "$F00_RUN_ID" "$F07_RUN_ID" "$F06_RUN_ID"; do
  RUN_DIR="artifacts/runs/$RUN_ID"
  python3 -m siminspect_bringup.acceptance --run-dir "$RUN_DIR"
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["overall"] == "passed"' "$RUN_DIR/acceptance.json"
  (cd "$RUN_DIR" && sha256sum --check SHA256SUMS)
  ! pgrep -af "$RUN_ID"
done
```

Then exercise interruption:

```bash
timeout --signal=INT --kill-after=20s 30s ./run_demo.sh --headless --scenario F00 --seed 21
```

Expected: interrupted command exits non-zero, preserves failed `acceptance.json`, `events.jsonl`, and logs, and leaves no owned process.

- [ ] **Step 5: Commit the runtime tests and stable configuration**

Do not commit `artifacts/runs/`.

```bash
git add config/demo_config.yaml src/siminspect_bringup
git commit -m "test: enforce demo Gate B and Gate C"
```

## Final Verification

- [ ] Run all focused tests:

```bash
python3 -m pytest \
  src/siminspect_bringup/test \
  src/siminspect_mission/test/test_mission_executor.py \
  src/siminspect_mission/test/test_report_writer.py \
  src/siminspect_viewpoint_planner/test/test_p2_selector.py \
  src/siminspect_gauge_vision/test/test_gauge_vision_node_contract.py \
  src/siminspect_benchmark/test/test_fault_injector.py \
  src/siminspect_benchmark/test/test_fault_image_relay.py -q
```

- [ ] Run `colcon build`, `colcon test --return-code-on-test-failure`, and `colcon test-result --all --verbose` in the Ubuntu container and require zero failures.
- [ ] Run one accepted F00 headless mission, one accepted F07 reinspection mission, one accepted F06 recovery mission, and one accepted `--visual --record` mission.
- [ ] Confirm every accepted run has `manifest.json`, `environment.json`, `config.yaml`, `acceptance.json`, `mission_report.json`, `events.jsonl`, component logs, and valid checksums.
- [ ] Confirm `acceptance.json.overall == "passed"`, `manifest.json.git.dirty == false`, and no run-ID process remains.
- [ ] Confirm the recorded run's MP4 and five screenshots resolve through `media/index.json` and originate from the same run ID and commit.
