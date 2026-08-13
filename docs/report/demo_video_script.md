# Demo Video Script (3-5 min)

**Honest status**: this is a recording blueprint. The video itself must be
recorded in the Ubuntu/Gazebo runtime (OI-005); nothing in this document
claims it has been recorded yet.

Total: ~4 minutes. Structure follows docs/19_APPLICATION_PACKAGING.md (8 steps).

## Step 1 — System architecture (0:00-0:10)

- **Shot**: `docs/report/architecture.png` full screen, camera slowly zooms out.
- **Narration**: "SimInspect-X is a simulation-first autonomous inspection
  robot. Eight layers: Gazebo sensors, EKF and SLAM state estimation, Nav2
  navigation, perception-aware viewpoint planning, PID or MPC precision
  control, gauge vision, a fault-tolerant mission executive — and a
  benchmark firewall that keeps simulator ground truth out of the robot."

## Step 2 — Plant, map and sensors (0:10-0:40)

- **Shot**: Gazebo plant world top-down view; robot drives a short path;
  RViz shows the SLAM map, laser scan and costmaps building up.
- **Narration**: "The robot runs in a headless Gazebo plant with analog
  gauges on six assets. It maps the environment with SLAM, localises with a
  wheel-IMU EKF, and plans with Nav2."

## Step 3 — Fixed viewpoint fails (0:40-1:10)

- **Shot**: split screen — the robot navigates to the fixed baseline
  waypoint; the camera view shows the gauge partially occluded by a pipe;
  the confidence readout drops below 0.80.
- **Narration**: "A fixed waypoint policy must accept whatever it sees. Here
  the fixed viewpoint is partially occluded, the reading confidence is low,
  and the baseline records a failed inspection."

## Step 4 — Proposed method selects another viewpoint (1:10-1:40)

- **Shot**: candidate viewpoints appear as markers around the gauge; the P2
  selector highlights the next-best candidate; the robot re-navigates and
  re-approaches.
- **Narration**: "The proposed policy scores every candidate by visibility,
  distance, incidence angle, clearance and travel cost. Low confidence
  triggers re-inspection: the current viewpoint is blacklisted and the
  next-best candidate is selected."

## Step 5 — Gauge reading succeeds (1:40-2:00)

- **Shot**: camera view of the gauge; the detector overlay (circle ROI),
  the needle angle, and the reading value with confidence appear on screen.
- **Narration**: "From the better viewpoint the gauge is fully visible. The
  detector finds the dial, the reader estimates the needle angle, and the
  mission records a valid reading with high confidence."

## Step 6 — Blocked-route recovery (2:00-2:30)

- **Shot**: a box is dropped across the planned route; Nav2 replans around
  it; the robot detours and continues the mission.
- **Narration**: "The mission must also survive infrastructure failures. When
  a route is blocked, Nav2 recovers and replans, and the mission executive
  keeps its bounded retries intact."

## Step 7 — PID vs MPC result plot (2:30-3:10)

- **Shot**: `results/plots/e5_pid_mpc.png` plus the PID/MPC summary table
  (final error, settling time, effort, violations), all regenerated from
  `experiments/raw/`.
- **Narration**: "The precision approach is benchmarked with PID against a
  constrained linear MPC under identical bounds and disturbances. The plot
  compares final pose error, settling time, control effort and constraint
  violations."

## Step 8 — End-to-end benchmark table (3:10-3:50)

- **Shot**: `results/plots/method_comparison.png` and the hypothesis-test
  table (H1-H4) from `results/analysis_summary.json`; the exported
  `mission_report.json` opens briefly.
- **Narration**: "Finally, the full experiment matrix: twelve seeded fault
  scenarios, paired trials, ablations, and statistical tests. Every number
  on screen is regenerated from raw trial files — the benchmark firewall
  guarantees the robot never saw the ground truth."

## Recording guide

- **Environment**: Ubuntu 24.04 container. Run `./run_demo.sh` for the live
  mission; capture RViz/Gazebo windows on the host with `DISPLAY` forwarded,
  or record headless render output.
- **Tools**: OBS Studio or SimpleScreenRecorder, 1080p; narration can be
  added in editing (script above).
- **Storage**: place the final video at `docs/report/demo_video.mp4` and link
  it from `README.md`.
- **Reproducibility**: every figure shown must be regenerated from
  `experiments/raw/` (docs/16); do not hand-edit plots.
- **Honesty**: until the Ubuntu run happens, the script remains a blueprint
  — do not publish a video with placeholder or fabricated footage.