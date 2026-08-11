# AGENTS.md — SimInspect-X Engineering Contract

## Mission

Build the project described in the repository blueprint. Optimise for:
1. admissions value;
2. technical correctness;
3. reproducibility;
4. measurable originality;
5. finishing the project.

## Non-negotiable rules

1. Do not replace the project thesis without an ADR.
2. Do not implement stretch features before the Gold Core is accepted.
3. ROS/Nav2/SLAM are infrastructure dependencies, not claims of originality.
4. Ground-truth simulator state is allowed for **benchmarking only**, never as an input to the autonomous robot.
5. Do not use simulator-hidden gauge values as perception input.
6. Every benchmark comparison must use paired scenarios/seeds where possible.
7. Do not fabricate performance numbers.
8. Failed trials stay in the dataset.
9. Never claim physical deployment or real digital-twin synchronisation.
10. External source/asset reuse requires licence and attribution review.
11. The system must have a CPU/headless benchmark mode.
12. The project must remain explainable to an admissions reviewer in under five minutes.

## Orchestrator workflow

Read in this order:
1. `.agent/PROJECT_STATE.md`
2. `.agent/TASK_LEDGER.md`
3. `.agent/DECISIONS.md`
4. `planning/MASTER_PLAN.md`
5. current phase specification
6. relevant architecture/interface docs

Preferred commands:
`/deep-plan -> /work-slice -> /verify-work -> /audit-work -> /handoff`

## Originality rule

Before adding a module, classify it:

- **INFRASTRUCTURE:** use mature package;
- **ADAPTATION:** configure/integrate existing package;
- **ORIGINAL:** implement + benchmark our own logic.

The project should spend most original effort on:
- viewpoint scoring/selection;
- adaptive re-inspection;
- precision control comparison;
- benchmark/fault-injection framework.

## Phase acceptance

No phase is ACCEPTED without:
- code/build evidence if code exists;
- automated tests;
- runtime evidence where relevant;
- metrics when relevant;
- updated docs/state;
- no unresolved critical contradiction.
