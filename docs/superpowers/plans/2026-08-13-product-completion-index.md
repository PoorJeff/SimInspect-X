# Product Completion Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the approved SimInspect-X product-completion design through reproducible runtime, real demo evidence, paired evaluation, and an evidence-backed bilingual GitHub release.

**Architecture:** The program is split into four ordered, independently reviewable plans. Each plan closes one evidence boundary and its gate before the next plan consumes its outputs; runtime artifacts and raw trials remain outside Git, while curated media, deterministic summaries, diagrams, and evidence locators enter the release commit.

**Tech Stack:** Ubuntu 24.04 VMware guest, Docker, ROS 2 Jazzy, Gazebo Harmonic, Nav2, SLAM Toolbox, Python 3, pytest, colcon, OSQP, ffmpeg, GitHub Actions, GitHub Releases.

## Global Constraints

- Preserve the existing project thesis; no ADR is required because this program closes runtime and presentation gaps without replacing the thesis.
- Use simulator ground truth only in the benchmark layer and never as autonomous input.
- Use paired method assignments with identical scenarios, conditions, and seeds.
- Retain experimental failures in raw data and retain infrastructure-failure records while blocking release on them.
- Support a CPU/headless benchmark and demo path.
- Do not claim physical deployment, a real synchronized digital twin, calibrated confidence, or validation of every F00-F11 scenario.
- Do not publish a numeric claim until it is generated from preserved raw trials.
- Do not call the project validated until Gates A-E pass on the release commit.

---

## Ordered Plans

1. [`2026-08-13-01-runtime-foundation.md`](2026-08-13-01-runtime-foundation.md) — repair Docker, rosdep, package install, tests, CI, and the ground-truth firewall; prove Gate A in a clean VM clone.
2. [`2026-08-13-02-demo-evidence.md`](2026-08-13-02-demo-evidence.md) — repair the real mission wiring, implement one visual/headless orchestrator, real F06/F07 effects, immutable artifacts, readiness, cleanup, recording, and Gates B/C.
3. [`2026-08-13-03-representative-evaluation.md`](2026-08-13-03-representative-evaluation.md) — implement one-trial evidence contracts, real B0/P2 and PID/MPC execution, strict paired completeness, deterministic summaries, and Gate D.
4. [`2026-08-13-04-github-release.md`](2026-08-13-04-github-release.md) — publish governance, attribution, diagrams, accepted-run media, English/Chinese product READMEs, deterministic bundles, and Gate E.

The execution dependency is strict:

```text
Gate A foundation
  -> real mission wiring and component smoke (Gate B)
  -> accepted headless/visual missions (Gate C)
  -> frozen paired evaluation (Gate D)
  -> bilingual evidence-backed release (Gate E)
```

### Task 1: Execute the reproducible foundation plan

**Files:**
- Read: `docs/superpowers/plans/2026-08-13-01-runtime-foundation.md`
- Produce: the exact files and evidence named in that plan.

**Interfaces:**
- Produces: a clean public SHA whose Docker build, strict colcon suite, firewall, VM validation, and GitHub Actions run all pass.
- Required by: Tasks 2-4.

- [ ] **Step 1: Execute every checkbox in Plan 01 in order**

Run the plan with `superpowers:subagent-driven-development` or `superpowers:executing-plans`; stop on the first red acceptance command.

- [ ] **Step 2: Verify the Plan 01 exit contract**

```bash
docker build --pull -f docker/Dockerfile -t siminspect-x:gate-a .
docker run --rm --user root -e DISPLAY= \
  -v "$PWD:/home/siminspect/ws" -w /home/siminspect/ws \
  siminspect-x:gate-a bash -lc \
  './scripts/verify_container_contract.sh && ./scripts/verify_foundation.sh'
test -z "$(git status --porcelain)"
```

Expected: exit 0 and the same SHA is green in GitHub Actions.

- [ ] **Step 3: Record the gate checkpoint**

```bash
git log -1 --format='%H %s'
git status --short
```

Do not begin Task 2 if either command reveals an uncommitted implementation change or the public CI result is red.

### Task 2: Execute the unified demo and evidence plan

**Files:**
- Read: `docs/superpowers/plans/2026-08-13-02-demo-evidence.md`
- Produce: the exact files and accepted run directories named in that plan.

**Interfaces:**
- Consumes: the green foundation SHA and target image from Task 1.
- Produces: real Gate B component evidence plus accepted Gate C F00, F06, and F07 runs; the F07 run contains real low-confidence alternative-viewpoint re-inspection.
- Required by: Tasks 3-4.

- [ ] **Step 1: Execute every checkbox in Plan 02 in order**

Implementation order inside the plan is part of the contract: close mission wiring before adding readiness/supervision, pass headless before visual, and pass visual before recording.

- [ ] **Step 2: Verify the public CLI contract**

```bash
./run_demo.sh --headless --method P2 --scenario F00 --seed 21
./run_demo.sh --visual --method P2 --scenario F06 --seed 21
./run_demo.sh --visual --record --method P2 --scenario F07 --seed 21
```

Expected: each prints an immutable run ID; every required `acceptance.json` is `passed`, and no orchestrator-owned process remains.

- [ ] **Step 3: Verify the Gate C semantic evidence**

```bash
python3 -m siminspect_bringup.acceptance \
  --artifact-root artifacts/runs \
  --require-scenario F00 --require-scenario F06 --require-scenario F07 \
  --require-accepted
```

Expected: six assets per run, bounded results for all assets, at least one camera reading, return-home evidence, a different F07 viewpoint on re-inspection, and valid media checksums for recorded runs.

### Task 3: Execute the representative evaluation plan

**Files:**
- Read: `docs/superpowers/plans/2026-08-13-03-representative-evaluation.md`
- Produce: the exact raw-trial, summary, claims, provenance, and plot outputs named in that plan.

**Interfaces:**
- Consumes: the accepted real mission interface, F06/F07 actuator evidence, and OSQP runtime path from Task 2.
- Produces: 60 E4 records/30 pairs and 100 E5 records/50 pairs for one clean release-candidate SHA, with strict completeness and deterministic results.
- Required by: Task 4.

- [ ] **Step 1: Execute the development pool before touching final seeds**

Run the exact seed 21-23 commands in Plan 03.

Expected: 18 E4 records plus 30 E5 records, no infrastructure failure, real P2 re-inspection, and zero MPC fallback trials.

- [ ] **Step 2: Freeze code/configuration and execute every remaining Plan 03 checkbox**

Do not change controller, policy, fault, timeout, or analysis parameters after the first final-pool trial. A correction creates a new candidate commit and restarts all final seeds.

- [ ] **Step 3: Verify Gate D completeness**

```bash
RC_SHA="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --raw-root experiments/raw --commit "$RC_SHA" --strict
```

Expected:

```text
E4 records=60 pairs=30
E5 records=100 pairs=50
total records=160 pairs=80
missing=0 duplicate=0 unexpected=0 infrastructure_failed=0
mpc_fallback_trials=0
```

### Task 4: Execute the GitHub release plan

**Files:**
- Read: `docs/superpowers/plans/2026-08-13-04-github-release.md`
- Produce: the exact public files, deterministic archives, release assets, tag, and GitHub Release named in that plan.

**Interfaces:**
- Consumes: accepted run IDs and checksums from Task 2 plus raw-derived claims and plots from Task 3.
- Produces: an English-primary, Chinese-secondary product repository and a GitHub Release whose external evidence index binds the final tag SHA to archives and checksums.

- [ ] **Step 1: Execute the repository-content tasks in Plan 04**

Only accepted-run media may enter `docs/media/`; only `claims.json` may generate README performance values. Keep full MP4 and raw archives outside Git history.

- [ ] **Step 2: Commit the release candidate and rerun Gates A-D on its exact SHA**

```bash
RELEASE_SHA="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
./scripts/verify_foundation.sh
python3 scripts/validate_public_release.py --version v0.1.0 --strict
```

Rerun Plan 02 acceptance and the complete Plan 03 matrix with provenance set to `$RELEASE_SHA`. Regenerated values must match the committed claims; any difference blocks release and creates a new release-candidate commit.

- [ ] **Step 3: Resolve the commit self-reference with the two-layer index**

The committed `docs/validation/evidence-index.json` records `v0.1.0`, relative repository paths, accepted run IDs, claims, and release asset names. The generated GitHub Release asset `release-evidence-index.json` records the tag's exact SHA, immutable release URLs, file sizes, and SHA-256 values. `manifest.json` and repository indexes exclude their own checksum field.

- [ ] **Step 4: Verify and publish Gate E**

Run the exact bundle, signed/annotated tag, GitHub Release, and post-publish link checks in Plan 04. Gate E passes only if the public tag SHA has green CI and every evidence locator resolves.

## Program Acceptance

The project is product-complete only when all of the following are true on tag `v0.1.0`:

- Gate A: clean-clone Docker build, build/tests/firewall, and public CI pass.
- Gate B: required ROS/Gazebo components and real OSQP MPC are ready.
- Gate C: accepted F00/F06/F07 missions exist; F07 proves alternative-viewpoint re-inspection; processes clean up.
- Gate D: 160 records and 80 complete pairs validate with no infrastructure failure or MPC fallback.
- Gate E: both READMEs agree, claims resolve to raw-derived evidence, media resolves to accepted runs, diagrams and governance files exist, and the GitHub Release index binds every large asset to the final SHA and checksum.

Until that point, the public status remains `implementation complete; runtime validation in progress` and names the first unpassed gate.
