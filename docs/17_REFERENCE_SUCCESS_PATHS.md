# Reference Success Paths

Use these as engineering/research patterns, not as work to relabel.

## A. AutoInspect
Lesson:
A serious inspection system contains mapping/localisation, graph/mission autonomy, inspection points, scheduling and
long-term robustness. "Robot can navigate" is not the final system.

Adopt:
mission-level structure and failure/recovery mindset.

## B. Sight Over Site
Lesson:
Inspection is not identical to reaching a coordinate. The robot needs a viewpoint that actually observes the target.

Adopt:
the **problem formulation** that target visibility/view quality matters.

Do not copy:
their end-to-end RL solution; our version deliberately uses interpretable geometry + confidence to stay feasible.

## C. Graph Inspection planning work
Lesson:
Inspection order/viewpoint selection can be formulated as an optimisation problem.

Adopt:
optional route/viewpoint optimisation after the core system is stable.

## D. Nav2
Lesson:
Reuse mature navigation servers, planners, controllers, costmaps and Behaviour Trees.

Adopt:
commodity navigation infrastructure; customize application behaviour.

## E. robot_localization + SLAM Toolbox
Lesson:
keep estimation, mapping and TF semantics correct.

## F. Industrial gauge-reading research
Lesson:
gauge reading is a real robotic inspection task with measurable numeric output.

Adopt:
a gauge-reading task with controlled simulation truth.

## Reuse protocol
For copied code/assets:
- check licence;
- preserve notices;
- record source/version;
- describe modifications;
- keep original contribution distinct.
