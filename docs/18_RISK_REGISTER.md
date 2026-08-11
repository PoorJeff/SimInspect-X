# Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Looks like a Nav2 tutorial | critical | viewpoint planner + adaptive inspection is flagship |
| Too much scope | critical | Gold Core / Research Edge / Stretch tiers |
| Gauge rendering becomes hard | high | start with generated 2D image tests before Gazebo integration |
| MPC integration consumes weeks | high | standalone precision benchmark accepted; plugin is optional |
| Viewpoint score too heuristic | medium | document terms, compare baselines, ablate terms |
| Confidence metric is weak | medium | call it confidence proxy unless calibrated |
| Simulator truth leaks into autonomy | critical | benchmark namespace firewall + dependency test |
| Overclaiming digital twin | medium | simulation-first wording |
| Low GPU capability | medium | simple Gazebo world, headless experiments |
| Research result shows no improvement | medium | result still valid; analyse failure/trade-off, do not manipulate data |
