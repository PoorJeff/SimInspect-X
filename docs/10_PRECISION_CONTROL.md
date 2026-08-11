# Precision Approach Control

## Motivation
Nav2 gets the robot near the inspection region.
The final camera viewpoint may need tighter position/yaw tolerances.

## Handoff
When:
- global goal is within approach radius;
- path is safe;
- precision controller is healthy;

switch to precision approach.

## Baseline controller
PID-style control on:
- position/cross-track error;
- heading error.

Include:
- output saturation;
- rate limit;
- anti-windup if integral term used.

## MPC controller

Candidate state:
`[x, y, theta, v]`

Candidate input:
`[a, omega]`

Optimisation objective:
- terminal/trajectory position error;
- yaw error;
- control magnitude;
- control smoothness.

Constraints:
- velocity;
- angular velocity;
- acceleration;
- optional approach-region constraints.

## Fair experiment

Same:
- target pose;
- starting state;
- dt;
- actuator bounds;
- noise seed;
- timeout.

## Metrics
- final position error;
- final yaw error;
- tracking RMSE;
- settling/completion time;
- control effort;
- constraint violations;
- CPU solve time;
- failure rate.

## Integration caution
The project must remain complete if MPC plugin integration becomes time-consuming.
Standalone precision-control mode is enough for the academic benchmark if the handoff interface is demonstrated.
