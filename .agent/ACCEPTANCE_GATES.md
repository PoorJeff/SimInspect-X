# ACCEPTANCE GATES

## P0
- one primary research question;
- explicit fixed-waypoint baseline;
- viewpoint score terms defined;
- gauge ground truth and autonomy inputs separated;
- precision-control takeover conditions defined;
- success/failure definitions frozen;
- stretch scope deferred.

## P1
- clean `colcon build`;
- tests can run headless;
- CI green;
- no package dependency cycles.

## P2
- robot moves from command;
- all core sensors publish;
- 5–8 gauge assets exist;
- each asset has machine-readable metadata;
- candidate viewpoints are visualised.

## P3
- EKF works;
- map build/save works;
- saved-map localisation works;
- localisation error is measured against benchmark-only ground truth.

## P4
- autonomous goal navigation works;
- at least one blocked-path recovery works;
- no teleoperation in benchmark runs.

## P5
- gauge-reading dataset generation is reproducible;
- detector/reader tested on held-out synthetic scenes;
- reading error and confidence metric exist;
- hidden true gauge value is not accessible to the reader.

## P6
- fixed waypoint baseline implemented;
- viewpoint-aware method implemented;
- low-confidence alternative-viewpoint logic works;
- comparison uses identical missions/seeds.

## P7
- both PID and MPC obey same velocity/acceleration bounds;
- same initial states/references/disturbances;
- benchmark includes tracking error, control effort, completion/failure, compute time;
- controller handoff does not destabilise the robot.

## P8
- mission of >=5 assets;
- inspection record per asset;
- bounded retries;
- return-home;
- machine-readable report.

## P9
- >=5 fault classes;
- repeatable seed sweeps;
- at least 3 meaningful ablations;
- all report plots generated from raw result files.

## P10
- one-command demo;
- architecture figure;
- 3–5 min video;
- complete technical report;
- CV/SOP claims trace to measurements.
