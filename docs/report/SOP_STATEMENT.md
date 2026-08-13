# Statement of Purpose

SimInspect-X is a simulation-first autonomous inspection robot for industrial
analog gauges, built to demonstrate that a perception-aware policy can turn a
generic "navigate and look" task into a closed, measurable inspection system.
In a headless Gazebo industrial plant, a differential-drive robot localises
with a wheel-IMU EKF and SLAM, navigates with Nav2, and for each gauge chooses
where to stand among candidate viewpoints scored by visibility, distance,
incidence angle, clearance and travel cost. A low-confidence reading triggers
adaptive re-inspection from the next-best viewpoint instead of a failed
inspection. The final alignment is executed by either a tuned PID controller
or a constrained linear MPC under matched conditions, so the control
comparison is scientific rather than anecdotal. Robustness is evaluated
through twelve seeded fault scenarios, paired trials and ablations, with all
figures regenerated from raw trial files and simulator ground truth firewalled
from the robot. The system is designed, implemented and unit-tested end to end
behind a one-command headless demo; the runtime evaluation on the Ubuntu
target is pending, and every numeric claim is withheld until that data exists
(see the Claim boundary in `docs/report/REPORT.md`).