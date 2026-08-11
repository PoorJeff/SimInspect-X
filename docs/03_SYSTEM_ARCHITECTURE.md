# System Architecture

```text
                     ┌─────────────────────────┐
                     │ Mission Executive       │
                     │ assets / retries / home │
                     └────────────┬────────────┘
                                  │
                     ┌────────────v────────────┐
                     │ Inspection Planner      │
                     │ candidate viewpoints    │
                     │ visibility / quality    │
                     └────────────┬────────────┘
                                  │ chosen viewpoint
                ┌─────────────────v────────────────┐
                │ Global / Local Navigation (Nav2) │
                │ planner + costmaps + MPPI + BT   │
                └─────────────────┬────────────────┘
                                  │ near-viewpoint handoff
                ┌─────────────────v────────────────┐
                │ Precision Approach Control       │
                │ PID baseline OR constrained MPC  │
                └─────────────────┬────────────────┘
                                  │ aligned pose
                     ┌────────────v────────────┐
                     │ Gauge Vision           │
                     │ detect / rectify / read│
                     │ value + confidence     │
                     └────────────┬────────────┘
                                  │
                    confidence OK?│
                          no ┌─────┴─────┐ yes
                             │           │
                             v           v
                   choose another      record
                      viewpoint        result

Robot foundation:
Gazebo -> wheel odom / IMU / LiDAR / camera
       -> EKF / SLAM / localisation
       -> TF / Nav2
```

## Deliberate separation of responsibilities

### Nav2
Reliable commodity navigation.

### Inspection Planner
Inspection-specific decision making.

### Precision Control
Control-theory evidence.

### Gauge Vision
Machine-vision evidence.

### Mission Executive
Automation/system integration.

### Benchmark
Truth access, fault injection, experimental evidence.
