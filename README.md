# SimInspect-X
## Perception-Aware Autonomous Industrial Inspection in a Simulation-First Plant Testbed

**One-sentence project claim**

> A ROS 2 autonomous mobile inspection robot that localises and navigates in a simulated industrial plant, chooses
> inspection viewpoints based on visibility and expected image quality, precisely approaches those viewpoints using
> classical or predictive control, reads industrial gauges from camera images, adapts when an inspection is uncertain,
> and quantifies robustness under repeatable faults.

This is intentionally **not** a tutorial-clone project. The mature ROS 2 ecosystem is reused for commodity robotics
infrastructure; the project’s original engineering and research contribution is concentrated in:

1. **perception-aware inspection viewpoint selection**;
2. **adaptive re-inspection based on visual confidence**;
3. **precision approach control: PID vs MPC**;
4. **mission-level recovery and experiment methodology**.

## Why this version is stronger than a generic inspection robot

A generic system says:

```text
Waypoint -> Nav2 -> Camera -> Classification
```

SimInspect-X asks a harder and more inspection-specific question:

```text
Which viewpoint should I inspect from?
        ↓
Can I reach it safely?
        ↓
Can I align precisely enough?
        ↓
Is the target actually readable?
        ↓
If not, where should I move next?
```

That turns the project from "ROS integration" into a coherent robotics research system.

## Flagship research question

> Can a perception-aware inspection policy reduce failed/low-quality inspections compared with fixed predefined
> waypoints, while controlling extra travel time and maintaining mission reliability?

## Secondary control question

> For the final precision-approach stage, when does constrained MPC improve viewpoint alignment relative to a
> well-tuned classical PID-style controller?

## Core demonstration

The final demonstration should show:

1. the robot starts in a mapped industrial plant;
2. receives a mission containing 5–8 gauge assets;
3. schedules / visits them;
4. selects a valid candidate camera viewpoint for each gauge;
5. navigates to the local approach region with Nav2;
6. performs final alignment using the selected precision controller;
7. reads the gauge value and estimates confidence;
8. if confidence is insufficient, chooses a different viewpoint and re-inspects;
9. survives at least one blocked-route or degraded-visibility event;
10. returns home and exports a structured inspection report.

## Locked baseline stack

- Ubuntu 24.04 LTS
- ROS 2 Jazzy
- Gazebo Harmonic
- ros_gz
- ros2_control / gz_ros2_control
- robot_localization
- SLAM Toolbox
- Nav2
- MPPI for production local navigation
- custom `inspection_planner`
- custom `precision_control`
- custom `gauge_reader`
- Python + C++ where appropriate

See:
- `docs/01_PROJECT_THESIS.md`
- `docs/02_ADMISSIONS_ALIGNMENT.md`
- `docs/04_ORIGINALITY_BOUNDARY.md`
- `planning/MASTER_PLAN.md`
- `.agent/`
