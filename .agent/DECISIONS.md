# DECISIONS / ADR SUMMARY

## ADR-001 Platform
Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic.
Reason: stable long-support ROS release and official Jazzy/Harmonic pairing.

## ADR-002 Robot
Differential-drive AMR.
Reason: maximises autonomy/control content without mechanical over-scope.

## ADR-003 Inspection task
Core inspection task is **camera-based analog gauge reading** with simulator-known ground truth.
Reason:
- industrially plausible;
- exact quantitative ground truth;
- no dependence on expensive external datasets;
- creates a natural viewpoint-quality problem;
- integrates vision, control and mission planning.

## ADR-004 Perception-aware planning
Each asset has multiple candidate inspection viewpoints.
The system scores candidates using geometry/visibility/safety/image-quality terms and selects a feasible viewpoint.
If reading confidence is low, the robot may select an alternative candidate.

## ADR-005 Ground truth
Gazebo ground truth and hidden gauge value may be read only by benchmark/evaluation nodes.
Autonomy/perception nodes cannot consume those topics.

## ADR-006 Navigation
Nav2 handles global navigation and general obstacle avoidance.
MPPI is the production local controller.

## ADR-007 Precision control
Within a configurable approach radius near the chosen inspection pose, a dedicated controller may take over.
Two controllers are implemented for study:
- PID-style baseline;
- constrained linear MPC.

## ADR-008 "Digital twin"
Public wording:
"simulation-first plant testbed" or "digital-twin-style testbed".
Do not claim a true real-asset-synchronised digital twin.

## ADR-009 AI scope
Deep anomaly detection and LLM mission parsing are optional stretch features only.
The core must be complete without them.
