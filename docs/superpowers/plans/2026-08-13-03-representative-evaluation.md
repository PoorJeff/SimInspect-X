# Representative Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a strict, reproducible Gate D dataset containing real B0/P2 mission trials and single-condition PID/MPC trials, then regenerate deterministic summaries and plots exclusively from preserved raw records.

**Architecture:** Add a release-only matrix and immutable batch-scoped raw-record contract without replacing the broader E1-E6 research matrix. A single-trial runner dispatches either the accepted unified demo interface for E4 or the precision simulator for E5, always writes a record even on infrastructure failure, and refuses to overwrite a prior record. A strict validator checks the complete paired assignment before a deterministic result builder emits the curated release summary, claims, provenance, checksums, and plots.

**Tech Stack:** Python 3.12, ROS 2 Jazzy, Gazebo Harmonic, Nav2, pytest, colcon, PyYAML, NumPy, SciPy, OSQP, Matplotlib Agg, Bash.

## Global Constraints

- Run this plan only after Plans 01 and 02 have passed Gates A-C on Ubuntu 24.04 and the unified demo accepts `--headless`, `--method`, `--scenario`, `--seed`, and `--artifact-root`.
- Use development seeds 21-25 only for tuning; this plan's candidate gate uses seeds 21-23 and does not touch final seeds until behavior and parameters are frozen.
- The final representative E4 matrix is B0/P2 x F00/F06/F07 x seeds 1-10: exactly 60 completed raw records and 30 complete pairs.
- The final representative E5 matrix is PID/MPC x five frozen conditions x seeds 1-10: exactly 100 completed raw records and 50 complete pairs.
- B0 and P2 must drive the same real mission interface and real Nav2 goals; an in-process selector-only benchmark, an empty pose, or an artificial offset is not evidence.
- F06 must physically block the fixed viewpoint, and F07 must modify the camera-to-reader image path; metadata-only fault activation is not evidence.
- PID and MPC use identical targets, initial states, timestep, timeout, bounds, and disturbance realizations for each condition/seed pair.
- An MPC trial is valid only when OSQP solves at least one optimization and uses zero fallback commands.
- Experimental outcome failures remain completed observations and stay in every denominator. Infrastructure failures remain on disk and block the selected batch from release.
- The benchmark layer alone may consume simulator ground truth; no production package or mission report may receive a ground-truth input.
- Raw trials and run artifacts stay outside Git. Only deterministic curated outputs under `results/release/v0.1.0/` are committed.
- Do not publish any numeric claim until strict validation has accepted all 160 final-pool records for one clean commit and one batch ID.

---

## File Structure

- `src/siminspect_benchmark/config/release_matrix.yaml` — the narrow product-release assignment and required-metric contract.
- `src/siminspect_benchmark/siminspect_benchmark/release_core.py` — immutable `TrialSpec`, matrix expansion, seed isolation, pair keys, and raw paths.
- `src/siminspect_benchmark/siminspect_benchmark/trial_schema.py` — schema-v2 record construction, semantic validation, checksums, and atomic no-overwrite writes.
- `src/siminspect_benchmark/siminspect_benchmark/e4_trial.py` — adapter from one E4 assignment to one real accepted demo run and benchmark-derived metrics.
- `src/siminspect_benchmark/siminspect_benchmark/e5_trial.py` — adapter from one E5 assignment to exactly one PID or MPC simulation.
- `src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py` — one-assignment dispatcher that preserves every failure record.
- `src/siminspect_benchmark/siminspect_benchmark/run_seed_sweep.py` — batch manifest, matrix iteration, progress accounting, and strict exit behavior.
- `src/siminspect_benchmark/siminspect_benchmark/validate_release_data.py` — exact-commit/batch completeness, duplicate, provenance, pairing, and OSQP validation.
- `src/siminspect_benchmark/siminspect_benchmark/build_release_results.py` — deterministic summary, neutral claims, provenance, and checksum generation.
- `src/siminspect_benchmark/siminspect_benchmark/generate_plots.py` — four deterministic headless SVG release plots.
- `src/siminspect_benchmark/test/test_release_matrix.py` — 48-development/160-final expansion and seed-pool contracts.
- `src/siminspect_benchmark/test/test_trial_schema.py` — schema, immutability, and failure-preservation contracts.
- `src/siminspect_benchmark/test/test_e4_trial.py` — real-demo command and accepted-artifact metric extraction contracts.
- `src/siminspect_benchmark/test/test_e5_trial.py` — single-trial, matched-disturbance, and OSQP diagnostic contracts.
- `src/siminspect_benchmark/test/test_release_validation.py` — strict completeness and pairing contracts.
- `src/siminspect_benchmark/test/test_release_results.py` — raw-only deterministic summary and plot contracts.
- `experiments/raw/$COMMIT/$BATCH_ID/...` — immutable batch-scoped records; every retry uses a new batch ID so rejected batches remain preserved.
- `results/release/v0.1.0/` — tracked candidate summary, claims, provenance, raw checksums, and plots.

### Task 1: Freeze the representative matrix and assignment API

**Files:**
- Create: `src/siminspect_benchmark/config/release_matrix.yaml`
- Create: `src/siminspect_benchmark/siminspect_benchmark/release_core.py`
- Create: `src/siminspect_benchmark/test/test_release_matrix.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:6-16`
- Modify: `docs/12_EXPERIMENT_PROTOCOL.md:74-94`
- Modify: `docs/16_REPRODUCIBILITY.md:17-29`
- Modify: `experiments/README.md:1-7`

**Interfaces:**
- Produces: `TrialSpec(experiment: str, method: str, scenario: str, condition: str, seed: int)`.
- Produces: `load_release_matrix(path: str | Path) -> dict`.
- Produces: `validate_release_matrix(matrix: dict) -> list[str]`.
- Produces: `iter_release_trials(matrix: dict, pool: str) -> list[TrialSpec]`.
- Produces: `TrialSpec.pair_key() -> tuple[str, str, str, int]` and `TrialSpec.relative_path() -> Path`.
- Required by: Tasks 2-8.

- [ ] **Step 1: Write the exact release-matrix fixture**

Create `src/siminspect_benchmark/config/release_matrix.yaml` with:

```yaml
schema_version: "1.0"
seed_pools:
  development: [21, 22, 23]
  final: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
experiments:
  E4:
    name: viewpoint_policy
    methods: [B0, P2]
    scenarios: [F00, F06, F07]
    conditions: [mission]
    required_metrics:
      - valid_read_rate
      - gauge_mae
      - path_length_m
      - mission_time_s
      - reinspection_count
      - recovery_count
      - station_completion_ratio
  E5:
    name: precision_control
    methods: [PID, MPC]
    scenarios: [F00]
    conditions:
      - E5_nominal
      - E5_yaw_error
      - E5_measurement_noise
      - E5_wheel_slip
      - E5_saturation
    required_metrics:
      - success
      - final_position_error
      - final_yaw_error
      - settling_time_s
      - effort_abs
      - effort_sq
      - constraint_violations
      - steps
```

- [ ] **Step 2: Write failing expansion and seed-isolation tests**

Create `src/siminspect_benchmark/test/test_release_matrix.py` with these core tests:

```python
from pathlib import Path
import sys

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "siminspect_benchmark"
sys.path.insert(0, str(PACKAGE))

from release_core import (  # noqa: E402
    TrialSpec,
    iter_release_trials,
    load_release_matrix,
    validate_release_matrix,
)

MATRIX_PATH = Path(__file__).resolve().parents[1] / "config" / "release_matrix.yaml"


def test_development_pool_expands_to_48_records_and_24_pairs():
    specs = iter_release_trials(load_release_matrix(MATRIX_PATH), "development")
    assert len(specs) == 48
    assert len({spec.pair_key() for spec in specs}) == 24
    assert {spec.seed for spec in specs} == {21, 22, 23}


def test_final_pool_expands_to_160_records_and_80_pairs():
    specs = iter_release_trials(load_release_matrix(MATRIX_PATH), "final")
    assert len(specs) == 160
    assert len({spec.pair_key() for spec in specs}) == 80
    e4 = [spec for spec in specs if spec.experiment == "E4"]
    e5 = [spec for spec in specs if spec.experiment == "E5"]
    assert len(e4) == 60
    assert len(e5) == 100


def test_pair_key_excludes_method_but_includes_condition():
    a = TrialSpec("E5", "PID", "F00", "E5_nominal", 1)
    b = TrialSpec("E5", "MPC", "F00", "E5_nominal", 1)
    c = TrialSpec("E5", "MPC", "F00", "E5_yaw_error", 1)
    assert a.pair_key() == b.pair_key()
    assert a.pair_key() != c.pair_key()


def test_matrix_rejects_overlapping_seed_pools():
    matrix = load_release_matrix(MATRIX_PATH)
    matrix["seed_pools"]["development"] = [10, 21, 22]
    assert "seed pools overlap: [10]" in validate_release_matrix(matrix)


def test_matrix_rejects_duplicate_assignments():
    matrix = load_release_matrix(MATRIX_PATH)
    matrix["experiments"]["E4"]["methods"] = ["B0", "B0"]
    assert "E4.methods contains duplicates" in validate_release_matrix(matrix)


def test_unknown_pool_is_rejected():
    with pytest.raises(ValueError, match="unknown seed pool"):
        iter_release_trials(load_release_matrix(MATRIX_PATH), "training")
```

- [ ] **Step 3: Run the tests and verify the module is absent**

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_release_matrix.py -vv
```

Expected: FAIL while importing `release_core`.

- [ ] **Step 4: Implement the immutable assignment core**

Create `release_core.py` around this exact public shape:

```python
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import yaml


@dataclass(frozen=True, order=True)
class TrialSpec:
    experiment: str
    method: str
    scenario: str
    condition: str
    seed: int

    def pair_key(self) -> tuple[str, str, str, int]:
        return self.experiment, self.scenario, self.condition, self.seed

    def relative_path(self) -> Path:
        experiment_dir = {
            "E4": "E4_viewpoint_policy",
            "E5": "E5_precision_control",
        }[self.experiment]
        return (
            Path(experiment_dir)
            / self.method
            / self.scenario
            / self.condition
            / f"seed_{self.seed:04d}.json"
        )


def load_release_matrix(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        matrix = yaml.safe_load(stream)
    errors = validate_release_matrix(matrix)
    if errors:
        raise ValueError("invalid release matrix: " + "; ".join(errors))
    return matrix


def _duplicates(values: list) -> bool:
    return len(values) != len(set(values))


def validate_release_matrix(matrix: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(matrix, dict) or matrix.get("schema_version") != "1.0":
        return ["schema_version must be 1.0"]
    pools = matrix.get("seed_pools", {})
    if set(pools) != {"development", "final"}:
        errors.append("seed_pools must contain development and final")
    development = pools.get("development", [])
    final = pools.get("final", [])
    overlap = sorted(set(development) & set(final))
    if overlap:
        errors.append(f"seed pools overlap: {overlap}")
    if development != [21, 22, 23]:
        errors.append("development seeds must be [21, 22, 23]")
    if final != list(range(1, 11)):
        errors.append("final seeds must be 1-10")
    experiments = matrix.get("experiments", {})
    if set(experiments) != {"E4", "E5"}:
        errors.append("experiments must contain exactly E4 and E5")
    for experiment, config in experiments.items():
        for field in ("methods", "scenarios", "conditions", "required_metrics"):
            values = config.get(field, [])
            if not values:
                errors.append(f"{experiment}.{field} must not be empty")
            elif _duplicates(values):
                errors.append(f"{experiment}.{field} contains duplicates")
    return errors


def iter_release_trials(matrix: dict, pool: str) -> list[TrialSpec]:
    errors = validate_release_matrix(matrix)
    if errors:
        raise ValueError("invalid release matrix: " + "; ".join(errors))
    if pool not in matrix["seed_pools"]:
        raise ValueError(f"unknown seed pool: {pool}")
    specs: list[TrialSpec] = []
    for experiment, config in matrix["experiments"].items():
        assignments = product(
            config["methods"],
            config["scenarios"],
            config["conditions"],
            matrix["seed_pools"][pool],
        )
        specs.extend(
            TrialSpec(experiment, method, scenario, condition, int(seed))
            for method, scenario, condition, seed in assignments
        )
    return sorted(specs)
```

- [ ] **Step 5: Register and run the matrix tests**

Add to `src/siminspect_benchmark/CMakeLists.txt` inside `if(BUILD_TESTING)`:

```cmake
ament_add_pytest_test(test_release_matrix test/test_release_matrix.py)
```

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_release_matrix.py -vv
```

Expected: 6 tests pass and the final count is exactly 160.

- [ ] **Step 6: Update the experiment contract documents**

Add a `Representative product-release matrix` subsection to `docs/12_EXPERIMENT_PROTOCOL.md` that names the exact E4/E5 assignments and states that the larger E1-E6 matrix remains optional research work. Replace the single-file example in `docs/16_REPRODUCIBILITY.md` with the batch-scoped layout:

```text
experiments/raw/$COMMIT/$BATCH_ID/
  batch_manifest.json
  E4_viewpoint_policy/B0/F06/mission/seed_0001.json
  E4_viewpoint_policy/P2/F06/mission/seed_0001.json
  E5_precision_control/PID/F00/E5_nominal/seed_0001.json
  E5_precision_control/MPC/F00/E5_nominal/seed_0001.json
```

State in `experiments/README.md` that a new batch ID is mandatory for every retry, completed outcome failures are included in analysis, and infrastructure-failed batches cannot be published.

- [ ] **Step 7: Commit the release assignment contract**

```bash
git add src/siminspect_benchmark/config/release_matrix.yaml \
  src/siminspect_benchmark/siminspect_benchmark/release_core.py \
  src/siminspect_benchmark/test/test_release_matrix.py \
  src/siminspect_benchmark/CMakeLists.txt \
  docs/12_EXPERIMENT_PROTOCOL.md docs/16_REPRODUCIBILITY.md \
  experiments/README.md
git commit -m "test: freeze representative evaluation matrix"
```

### Task 2: Define immutable raw records and atomic failure preservation

**Files:**
- Create: `src/siminspect_benchmark/siminspect_benchmark/trial_schema.py`
- Create: `src/siminspect_benchmark/test/test_trial_schema.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:8-18`

**Interfaces:**
- Consumes: `TrialSpec` and the required metrics in `release_matrix.yaml`.
- Produces: `build_trial_record(spec, commit, execution_status, outcome, failure_reason, metrics, provenance, diagnostics) -> dict`.
- Produces: `validate_trial_record(record, spec, required_metrics) -> list[str]`.
- Produces: `record_path(raw_root, commit, batch_id, spec) -> Path`.
- Produces: `write_record_once(path, record) -> None`; raises `FileExistsError` instead of overwriting.
- Required by: Tasks 3-8.

- [ ] **Step 1: Write failing schema and immutability tests**

Create `test_trial_schema.py` with:

```python
from pathlib import Path
import json
import sys

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "siminspect_benchmark"
sys.path.insert(0, str(PACKAGE))

from release_core import TrialSpec  # noqa: E402
from trial_schema import (  # noqa: E402
    build_trial_record,
    record_path,
    validate_trial_record,
    write_record_once,
)


def _provenance():
    return {
        "batch_id": "final-20260813T120000Z",
        "matrix_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "harness": "e5_trial",
        "run_id": None,
        "artifact_paths": [],
        "started_at": "2026-08-13T12:00:00Z",
        "ended_at": "2026-08-13T12:00:01Z",
    }


def test_completed_outcome_failure_is_a_valid_observation():
    spec = TrialSpec("E5", "PID", "F00", "E5_nominal", 1)
    metrics = {
        "success": False,
        "final_position_error": 0.3,
        "final_yaw_error": 0.2,
        "settling_time_s": 30.0,
        "effort_abs": 3.0,
        "effort_sq": 2.0,
        "constraint_violations": 0,
        "steps": 600,
    }
    record = build_trial_record(
        spec=spec,
        commit="1" * 40,
        execution_status="completed",
        outcome="failure",
        failure_reason="controller_timeout",
        metrics=metrics,
        provenance=_provenance(),
        diagnostics={"solver_backend": "none"},
    )
    assert validate_trial_record(record, spec, list(metrics)) == []


def test_infrastructure_failure_requires_null_outcome_and_reason():
    spec = TrialSpec("E4", "P2", "F07", "mission", 1)
    record = build_trial_record(
        spec=spec,
        commit="1" * 40,
        execution_status="infrastructure_failed",
        outcome=None,
        failure_reason="demo exited 2",
        metrics={},
        provenance=_provenance(),
        diagnostics={"exit_code": 2},
    )
    assert validate_trial_record(record, spec, []) == []


def test_record_path_is_batch_scoped():
    spec = TrialSpec("E4", "B0", "F06", "mission", 1)
    assert record_path("experiments/raw", "1" * 40, "final-a", spec) == Path(
        "experiments/raw"
    ) / ("1" * 40) / "final-a" / spec.relative_path()


def test_writer_is_atomic_and_never_overwrites(tmp_path):
    path = tmp_path / "seed_0001.json"
    record = {"schema_version": "2.0", "value": 1}
    write_record_once(path, record)
    assert json.loads(path.read_text(encoding="utf-8"))["value"] == 1
    with pytest.raises(FileExistsError):
        write_record_once(path, {"schema_version": "2.0", "value": 2})
    assert json.loads(path.read_text(encoding="utf-8"))["value"] == 1


def test_schema_rejects_dry_run_and_short_commit():
    spec = TrialSpec("E4", "B0", "F00", "mission", 1)
    record = build_trial_record(
        spec, "abc", "dry_run", None, "", {}, _provenance(), {}
    )
    errors = validate_trial_record(record, spec, [])
    assert "git_commit must be a 40-character lowercase hex SHA" in errors
    assert "execution_status must be completed or infrastructure_failed" in errors
```

- [ ] **Step 2: Confirm the schema module is absent**

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_trial_schema.py -vv
```

Expected: FAIL while importing `trial_schema`.

- [ ] **Step 3: Implement schema-v2 records and no-overwrite writes**

Create `trial_schema.py` with these exact record fields:

```python
import json
import os
from pathlib import Path
import re
import tempfile

from siminspect_benchmark.release_core import TrialSpec

SCHEMA_VERSION = "2.0"
EXECUTION_STATUSES = {"completed", "infrastructure_failed"}
OUTCOMES = {"success", "failure"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def record_path(raw_root, commit: str, batch_id: str, spec: TrialSpec) -> Path:
    return Path(raw_root) / commit / batch_id / spec.relative_path()


def build_trial_record(
    spec: TrialSpec,
    commit: str,
    execution_status: str,
    outcome: str | None,
    failure_reason: str,
    metrics: dict,
    provenance: dict,
    diagnostics: dict,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment": spec.experiment,
        "method": spec.method,
        "scenario": spec.scenario,
        "condition": spec.condition,
        "seed": spec.seed,
        "git_commit": commit,
        "execution_status": execution_status,
        "outcome": outcome,
        "failure_reason": failure_reason,
        "metrics": metrics,
        "provenance": provenance,
        "diagnostics": diagnostics,
    }


def validate_trial_record(record: dict, spec: TrialSpec, required_metrics: list[str]) -> list[str]:
    errors: list[str] = []
    expected = {
        "experiment": spec.experiment,
        "method": spec.method,
        "scenario": spec.scenario,
        "condition": spec.condition,
        "seed": spec.seed,
    }
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 2.0")
    for key, value in expected.items():
        if record.get(key) != value:
            errors.append(f"{key} does not match assignment")
    if not SHA_RE.fullmatch(str(record.get("git_commit", ""))):
        errors.append("git_commit must be a 40-character lowercase hex SHA")
    status = record.get("execution_status")
    if status not in EXECUTION_STATUSES:
        errors.append("execution_status must be completed or infrastructure_failed")
    outcome = record.get("outcome")
    if status == "completed" and outcome not in OUTCOMES:
        errors.append("completed record requires success or failure outcome")
    if status == "infrastructure_failed" and outcome is not None:
        errors.append("infrastructure failure requires null outcome")
    if status == "infrastructure_failed" and not record.get("failure_reason"):
        errors.append("infrastructure failure requires a reason")
    if status == "completed":
        missing = sorted(set(required_metrics) - set(record.get("metrics", {})))
        if missing:
            errors.append(f"missing required metrics: {missing}")
    provenance = record.get("provenance") or {}
    for key in (
        "batch_id", "matrix_sha256", "config_sha256", "harness",
        "run_id", "artifact_paths", "started_at", "ended_at",
    ):
        if key not in provenance:
            errors.append(f"provenance missing {key}")
    return errors


def write_record_once(path: str | Path, record: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    handle, temporary = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
```

Use the package-relative fallback import pattern already present in `experiment_runner.py` so direct source-tree tests and installed ROS execution both work.

- [ ] **Step 4: Register and run the schema tests**

Add:

```cmake
ament_add_pytest_test(test_trial_schema test/test_trial_schema.py)
```

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_trial_schema.py -vv
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit the raw-record contract**

```bash
git add src/siminspect_benchmark/siminspect_benchmark/trial_schema.py \
  src/siminspect_benchmark/test/test_trial_schema.py \
  src/siminspect_benchmark/CMakeLists.txt
git commit -m "test: define immutable benchmark trial records"
```

### Task 3: Make the runner execute one assignment and preserve every failure

**Files:**
- Modify: `src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py:1-123`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/run_seed_sweep.py:1-84`
- Modify: `src/siminspect_benchmark/test/test_experiment_runner.py:1-92`

**Interfaces:**
- Consumes: `TrialSpec`, schema-v2, an exact 40-character commit, and one batch ID.
- Produces: `run_trial(spec, context, command_builder, timeout_s) -> tuple[dict, Path]`.
- Produces: one immutable JSON record for success, experimental failure, non-zero exit, timeout, signal, malformed harness output, or launch error.
- Produces: `run_seed_sweep` exit 0 only when every assignment has `execution_status=completed`; outcome failures do not change that exit code.
- Required by: Tasks 4-8.

- [ ] **Step 1: Replace the old wrapper tests with failure-preservation tests**

Keep the existing legacy-core tests that remain true, then add tests using a temporary harness command:

```python
from pathlib import Path
import json
import subprocess

from experiment_runner import RunContext, run_trial
from release_core import TrialSpec


def _context(tmp_path):
    return RunContext(
        raw_root=tmp_path,
        commit="1" * 40,
        batch_id="dev-test",
        matrix_sha256="a" * 64,
        config_sha256="b" * 64,
        artifact_root=tmp_path / "artifacts",
    )


def test_nonzero_harness_exit_is_written_as_infrastructure_failure(tmp_path):
    spec = TrialSpec("E4", "B0", "F00", "mission", 21)
    record, path = run_trial(
        spec,
        _context(tmp_path),
        command_builder=lambda _spec, _output, _ctx: ["python3", "-c", "raise SystemExit(7)"],
        required_metrics=[],
        timeout_s=5,
    )
    assert path.exists()
    assert record["execution_status"] == "infrastructure_failed"
    assert record["diagnostics"]["exit_code"] == 7


def test_timeout_is_written_and_not_raised(tmp_path):
    spec = TrialSpec("E4", "P2", "F07", "mission", 21)
    record, path = run_trial(
        spec,
        _context(tmp_path),
        command_builder=lambda _spec, _output, _ctx: [
            "python3", "-c", "import time; time.sleep(2)"
        ],
        required_metrics=[],
        timeout_s=0.01,
    )
    assert path.exists()
    assert record["execution_status"] == "infrastructure_failed"
    assert record["failure_reason"] == "harness_timeout"


def test_completed_outcome_failure_does_not_become_infrastructure_failure(tmp_path):
    output_payload = {
        "outcome": "failure",
        "failure_reason": "controller_timeout",
        "metrics": {"success": False},
        "diagnostics": {},
        "run_id": None,
        "artifact_paths": [],
    }
    script = (
        "import json,sys;"
        f"json.dump({output_payload!r},open(sys.argv[1],'w'))"
    )
    spec = TrialSpec("E5", "PID", "F00", "E5_nominal", 21)
    record, _ = run_trial(
        spec,
        _context(tmp_path),
        command_builder=lambda _spec, output, _ctx: ["python3", "-c", script, str(output)],
        required_metrics=["success"],
        timeout_s=5,
    )
    assert record["execution_status"] == "completed"
    assert record["outcome"] == "failure"
```

- [ ] **Step 2: Run the focused tests and observe the old API failure**

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_experiment_runner.py -vv
```

Expected: FAIL because `RunContext` and the new `run_trial` contract do not exist.

- [ ] **Step 3: Implement a one-assignment runner with unconditional record writing**

Replace the subprocess body with this control flow:

```python
@dataclass(frozen=True)
class RunContext:
    raw_root: Path
    commit: str
    batch_id: str
    matrix_sha256: str
    config_sha256: str
    artifact_root: Path


def run_trial(spec, context, command_builder, required_metrics, timeout_s=1800):
    destination = record_path(
        context.raw_root, context.commit, context.batch_id, spec
    )
    harness_output = destination.with_suffix(".harness.json")
    started_at = utc_now()
    execution_status = "infrastructure_failed"
    outcome = None
    failure_reason = "harness_not_started"
    metrics = {}
    diagnostics = {}
    run_id = None
    artifact_paths = []
    try:
        command = command_builder(spec, harness_output, context)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        diagnostics = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if completed.returncode != 0:
            failure_reason = f"harness_exit_{completed.returncode}"
        elif not harness_output.is_file():
            failure_reason = "harness_output_missing"
        else:
            payload = json.loads(harness_output.read_text(encoding="utf-8"))
            execution_status = "completed"
            outcome = payload["outcome"]
            failure_reason = payload.get("failure_reason", "")
            metrics = payload["metrics"]
            diagnostics.update(payload.get("diagnostics", {}))
            run_id = payload.get("run_id")
            artifact_paths = payload.get("artifact_paths", [])
    except subprocess.TimeoutExpired as exc:
        failure_reason = "harness_timeout"
        diagnostics = {
            "timeout_s": timeout_s,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "") if isinstance(exc.stderr, str) else "",
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        failure_reason = f"harness_protocol_error:{type(exc).__name__}:{exc}"
    finally:
        harness_output.unlink(missing_ok=True)
    provenance = {
        "batch_id": context.batch_id,
        "matrix_sha256": context.matrix_sha256,
        "config_sha256": context.config_sha256,
        "harness": "e4_trial" if spec.experiment == "E4" else "e5_trial",
        "run_id": run_id,
        "artifact_paths": artifact_paths,
        "started_at": started_at,
        "ended_at": utc_now(),
    }
    record = build_trial_record(
        spec, context.commit, execution_status, outcome, failure_reason,
        metrics, provenance, diagnostics,
    )
    errors = validate_trial_record(record, spec, required_metrics)
    if errors:
        record["execution_status"] = "infrastructure_failed"
        record["outcome"] = None
        record["failure_reason"] = "record_validation:" + ";".join(errors)
    write_record_once(destination, record)
    return record, destination
```

Use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` for `utc_now()`. Retain full stdout/stderr in the ignored raw record; do not truncate it to 500 characters.

- [ ] **Step 4: Make the sweep strict and batch-scoped**

Add CLI arguments:

```text
--matrix
--pool development|final
--batch-id
--commit
--raw-root
--artifact-root
--experiments E4 E5
--methods
--scenarios
--conditions
--seeds
```

Before the first trial, write `batch_manifest.json` with full commit, dirty-worktree flag, UTC start, pool, matrix checksum, selected specs, Python/ROS/OSQP versions, and command line. Reject an existing batch directory. Iterate `sorted(selected_specs)` and update the manifest counters after every record. Exit 2 if any record is `infrastructure_failed`; exit 0 when all assignments completed, including experimental outcome failures.

Use this summary line exactly:

```python
print(
    f"batch={batch_id} expected={len(specs)} completed={completed_count} "
    f"outcome_failed={outcome_failed_count} infrastructure_failed={infra_count}"
)
```

- [ ] **Step 5: Run the runner tests and dry command expansion**

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_experiment_runner.py \
  src/siminspect_benchmark/test/test_trial_schema.py -vv
python3 src/siminspect_benchmark/siminspect_benchmark/run_seed_sweep.py \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool development --batch-id command-check --commit "$(git rev-parse HEAD)" \
  --raw-root /tmp/siminspect-command-check --list-only
```

Expected: tests pass; list-only reports 48 assignments and writes no trial record.

- [ ] **Step 6: Commit the failure-preserving runner**

```bash
git add src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py \
  src/siminspect_benchmark/siminspect_benchmark/run_seed_sweep.py \
  src/siminspect_benchmark/test/test_experiment_runner.py
git commit -m "feat: preserve one record per benchmark assignment"
```

### Task 4: Adapt E4 to the real unified demo and benchmark evidence

**Files:**
- Create: `src/siminspect_benchmark/siminspect_benchmark/e4_trial.py`
- Create: `src/siminspect_benchmark/test/test_e4_trial.py`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:6-20`
- Retire from release dispatch only: `src/siminspect_benchmark/siminspect_benchmark/run_b0_benchmark.py:36-48`
- Retire from release dispatch only: `src/siminspect_benchmark/siminspect_benchmark/run_p2_benchmark.py:57-130`

**Interfaces:**
- Consumes: `./run_demo.sh --headless --benchmark-evidence --method METHOD --scenario SCENARIO --seed SEED --artifact-root ROOT` from Plan 02.
- Consumes: the final stdout token `RUN_ID=$RUN_ID` and the corresponding `manifest.json`, `acceptance.json`, `mission_report.json`, `events.jsonl`, and `benchmark_evaluation.json`.
- Produces: `build_demo_command(spec, artifact_root) -> list[str]`.
- Produces: `extract_run_id(stdout: str) -> str`.
- Produces: `evaluate_e4_run(run_dir: Path, spec: TrialSpec) -> dict`.
- Produces: a harness JSON with real E4 outcome, metrics, run ID, and evidence paths.
- Required by: Tasks 6-8.

- [ ] **Step 1: Write failing real-demo command and artifact tests**

Create `test_e4_trial.py` with:

```python
from pathlib import Path
import json
import sys

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "siminspect_benchmark"
sys.path.insert(0, str(PACKAGE))

from e4_trial import build_demo_command, evaluate_e4_run, extract_run_id  # noqa: E402
from release_core import TrialSpec  # noqa: E402


def test_b0_and_p2_use_the_same_real_demo_entrypoint(tmp_path):
    b0 = build_demo_command(TrialSpec("E4", "B0", "F06", "mission", 21), tmp_path)
    p2 = build_demo_command(TrialSpec("E4", "P2", "F06", "mission", 21), tmp_path)
    assert b0[0:2] == ["bash", "./run_demo.sh"]
    assert p2[0:2] == ["bash", "./run_demo.sh"]
    assert "--method" in b0 and b0[b0.index("--method") + 1] == "B0"
    assert "--method" in p2 and p2[p2.index("--method") + 1] == "P2"
    assert "run_b0_benchmark.py" not in b0
    assert "run_p2_benchmark.py" not in p2


def test_run_id_parser_requires_one_machine_readable_token():
    assert extract_run_id("log\nRUN_ID=run-123\n") == "run-123"
    with pytest.raises(ValueError, match="exactly one"):
        extract_run_id("no token")


def test_e4_metrics_come_from_accepted_artifacts(tmp_path):
    run = tmp_path / "run-123"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({
        "git": {"commit_sha": "1" * 40, "dirty": False},
        "method": "P2",
        "scenario": "F07",
        "seed": 21,
    }), encoding="utf-8")
    (run / "acceptance.json").write_text(json.dumps({
        "overall": "passed",
        "gates": [{"id": "mission", "status": "passed",
                   "reason": "complete", "evidence": ["mission_report.json"]}],
    }), encoding="utf-8")
    (run / "mission_report.json").write_text(json.dumps({
        "num_assets": 6,
        "num_results": 6,
        "mission_time_s": 180.0,
        "results": [
            {"asset_id": f"gauge_{index}", "attempts": 2 if index == 0 else 1,
             "status": "success"}
            for index in range(6)
        ],
    }), encoding="utf-8")
    (run / "events.jsonl").write_text(
        '{"event":"navigation_recovery"}\n', encoding="utf-8"
    )
    (run / "benchmark_evaluation.json").write_text(json.dumps({
        "valid_read_count": 5,
        "reading_count": 6,
        "absolute_errors": [1.0, 2.0, 1.5, 0.5, 1.0],
        "path_length_m": 25.0,
        "f07_camera_frames_modified": 120,
        "alternative_viewpoint_attempts": 1,
    }), encoding="utf-8")
    result = evaluate_e4_run(
        run, TrialSpec("E4", "P2", "F07", "mission", 21)
    )
    assert result["outcome"] == "success"
    assert result["metrics"]["valid_read_rate"] == pytest.approx(5 / 6)
    assert result["metrics"]["gauge_mae"] == pytest.approx(1.2)
    assert result["metrics"]["reinspection_count"] == 1
    assert result["metrics"]["recovery_count"] == 1


def test_f06_requires_physical_occluder_evidence(tmp_path):
    run = tmp_path / "run-f06"
    run.mkdir()
    for name, payload in {
        "manifest.json": {"git": {"commit_sha": "1" * 40, "dirty": False},
                          "method": "B0", "scenario": "F06", "seed": 21},
        "acceptance.json": {"overall": "passed", "gates": []},
        "mission_report.json": {"num_assets": 6, "num_results": 6,
                                "mission_time_s": 1.0, "results": []},
        "benchmark_evaluation.json": {"valid_read_count": 0, "reading_count": 0,
                                      "absolute_errors": [], "path_length_m": 0.0,
                                      "f06_occluder_spawned": False},
    }.items():
        (run / name).write_text(json.dumps(payload), encoding="utf-8")
    (run / "events.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="F06 physical occluder evidence missing"):
        evaluate_e4_run(run, TrialSpec("E4", "B0", "F06", "mission", 21))
```

- [ ] **Step 2: Run the tests and confirm the adapter is absent**

Run:

```bash
python3 -m pytest src/siminspect_benchmark/test/test_e4_trial.py -vv
```

Expected: FAIL while importing `e4_trial`.

- [ ] **Step 3: Implement the real-demo adapter**

`build_demo_command` must return:

```python
[
    "bash", "./run_demo.sh", "--headless",
    "--method", spec.method,
    "--scenario", spec.scenario,
    "--seed", str(spec.seed),
    "--benchmark-evidence",
    "--artifact-root", str(artifact_root),
]
```

`extract_run_id` must accept exactly one line beginning `RUN_ID=` and reject zero or multiple tokens. `evaluate_e4_run` must:

1. validate all five required files;
2. require `acceptance.json.overall == "passed"` for successful mission outcome;
3. require manifest method/scenario/seed to match `TrialSpec`, `manifest.git.dirty == false`, and a full `manifest.git.commit_sha`;
4. require `benchmark_evaluation.json` to be produced by `siminspect_benchmark` and never copy `true_value` into `mission_report.json`;
5. require `f06_occluder_spawned == true` and a non-empty occluder model identifier for F06;
6. require `f07_camera_frames_modified > 0` for F07;
7. require P2/F07 `alternative_viewpoint_attempts >= 1` and at least two distinct viewpoints for one asset;
8. calculate `valid_read_rate`, `gauge_mae`, `station_completion_ratio`, `reinspection_count`, and `recovery_count` with outcome failures retained in denominators;
9. return relative evidence paths, never copy the large run directory into Git.

The executable CLI is:

```bash
python3 -m siminspect_benchmark.e4_trial \
  --method P2 --scenario F07 --condition mission --seed 21 \
  --artifact-root artifacts/runs --output /tmp/e4-harness.json
```

It launches the command, preserves stdout/stderr, resolves the run ID, evaluates the run, writes one harness JSON, and exits non-zero only for infrastructure/protocol failure. A mission that completed but failed inspection criteria writes `outcome: failure` and exits zero.

- [ ] **Step 4: Route E4 assignments only through `e4_trial`**

In `experiment_runner.py`, use:

```python
def build_harness_command(spec, output, context):
    module = "siminspect_benchmark.e4_trial" if spec.experiment == "E4" \
        else "siminspect_benchmark.e5_trial"
    return [
        "python3", "-m", module,
        "--method", spec.method,
        "--scenario", spec.scenario,
        "--condition", spec.condition,
        "--seed", str(spec.seed),
        "--artifact-root", str(context.artifact_root),
        "--output", str(output),
    ]
```

Remove `run_b0_benchmark.py` and `run_p2_benchmark.py` from `HARNESS_MAP` or stop consulting that map for release-matrix dispatch. Keep the legacy files for historical/internal use; do not delete unrelated code.

- [ ] **Step 5: Install and test the E4 adapter**

Add `e4_trial.py` to the `install(PROGRAMS ...)` list and register:

```cmake
ament_add_pytest_test(test_e4_trial test/test_e4_trial.py)
```

Run:

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_e4_trial.py \
  src/siminspect_benchmark/test/test_experiment_runner.py -vv
```

Expected: all tests pass and neither release command references either legacy benchmark script.

- [ ] **Step 6: Run one development E4 smoke per method**

After sourcing the installed workspace:

```bash
SMOKE_SHA="$(git rev-parse HEAD)"
SMOKE_BATCH="e4-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
ros2 run siminspect_benchmark run_seed_sweep \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool development --batch-id "$SMOKE_BATCH" --commit "$SMOKE_SHA" \
  --raw-root experiments/raw --artifact-root artifacts/runs \
  --experiments E4 --methods B0 P2 --scenarios F00 --seeds 21
```

Expected: 2 completed records, 1 complete pair, two real accepted demo run IDs, and no infrastructure failure.

- [ ] **Step 7: Commit the real E4 adapter**

```bash
git add src/siminspect_benchmark/siminspect_benchmark/e4_trial.py \
  src/siminspect_benchmark/siminspect_benchmark/experiment_runner.py \
  src/siminspect_benchmark/test/test_e4_trial.py \
  src/siminspect_benchmark/CMakeLists.txt
git commit -m "feat: benchmark real B0 and P2 missions"
```

### Task 5: Make E5 single-trial, disturbance-paired, and OSQP-verifiable

**Files:**
- Create: `src/siminspect_benchmark/siminspect_benchmark/e5_trial.py`
- Create: `src/siminspect_benchmark/test/test_e5_trial.py`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/run_precision_benchmark.py:27-267`
- Modify: `src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py:42-106,236-259`
- Modify: `src/siminspect_precision_control/test/test_mpc_controller.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:6-22`

**Interfaces:**
- Produces: `generate_disturbance(condition: dict, seed: int, max_steps: int) -> dict[str, numpy.ndarray]`.
- Produces: `disturbance_digest(disturbance: dict) -> str`.
- Produces: `run_precision_trial(method: str, condition_id: str, seed: int, config: dict) -> dict`.
- Extends `MPCController` with read-only `solver_backend`, `solver_version`, `last_solver_status`, `solve_count`, and `fallback_count` diagnostics; `update(...)` keeps its existing 5-tuple return type.
- Required by: Tasks 6-8.

- [ ] **Step 1: Write failing single-trial and matched-disturbance tests**

Create `test_e5_trial.py` with:

```python
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parents[1] / "siminspect_benchmark"
sys.path.insert(0, str(PACKAGE))

from e5_trial import run_precision_trial  # noqa: E402


CONFIG = {
    "dt": 0.05,
    "max_steps": 20,
    "targets": [{"x": 0.1, "y": 0.0, "yaw": 0.0}],
    "conditions": [
        {"id": "E5_measurement_noise", "pos_noise_std": 0.01,
         "yaw_noise_std": 0.03},
    ],
}


def test_one_invocation_produces_exactly_one_method_condition_seed():
    result = run_precision_trial("PID", "E5_measurement_noise", 21, CONFIG)
    assert result["method"] == "PID"
    assert result["condition"] == "E5_measurement_noise"
    assert result["seed"] == 21
    assert "trials" not in result


def test_pair_uses_identical_disturbance_digest():
    pid = run_precision_trial("PID", "E5_measurement_noise", 21, CONFIG)
    mpc = run_precision_trial("MPC", "E5_measurement_noise", 21, CONFIG)
    assert pid["diagnostics"]["disturbance_sha256"] == \
        mpc["diagnostics"]["disturbance_sha256"]


def test_pid_reports_no_solver_backend():
    result = run_precision_trial("PID", "E5_measurement_noise", 21, CONFIG)
    assert result["diagnostics"]["solver_backend"] == "none"
    assert result["diagnostics"]["fallback_count"] == 0
```

Append focused MPC diagnostics tests to `test_mpc_controller.py`:

```python
def test_mpc_exposes_solver_diagnostics_after_update():
    controller = MPCController((0.2, 0.0, 0.0))
    controller.update((0.0, 0.0, 0.0), 0.05)
    assert controller.solver_backend in {"osqp", "unavailable"}
    assert controller.solve_count >= 0
    assert controller.fallback_count >= 0
    assert isinstance(controller.last_solver_status, str)
```

- [ ] **Step 2: Run the tests and observe the absent single-trial API**

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_e5_trial.py \
  src/siminspect_precision_control/test/test_mpc_controller.py -vv
```

Expected: FAIL while importing `e5_trial` and reading MPC diagnostics.

- [ ] **Step 3: Generate deterministic disturbances once per pair**

Replace global `np.random.seed` use with a local generator and precomputed arrays:

```python
def generate_disturbance(condition, seed, max_steps):
    rng = np.random.default_rng(seed)
    return {
        "x_noise": rng.normal(0.0, condition.get("pos_noise_std", 0.0), max_steps),
        "y_noise": rng.normal(0.0, condition.get("pos_noise_std", 0.0), max_steps),
        "yaw_noise": rng.normal(0.0, condition.get("yaw_noise_std", 0.0), max_steps),
    }


def disturbance_digest(disturbance):
    digest = hashlib.sha256()
    for key in sorted(disturbance):
        digest.update(key.encode("utf-8"))
        digest.update(np.asarray(disturbance[key], dtype="<f8").tobytes())
    return digest.hexdigest()
```

Change `simulate_robot` to consume the arrays by step index. Generate the same arrays independently from the same condition/seed for PID and MPC, record the digest, and never share mutable random state between methods.

- [ ] **Step 4: Add explicit OSQP diagnostics without changing controller output**

Initialize:

```python
self.solver_backend = "unavailable"
self.solver_version = ""
self.last_solver_status = "not_run"
self.solve_count = 0
self.fallback_count = 0
```

When OSQP imports, set backend/version. After each solve, store `result.info.status`; increment `solve_count` only for status values 1 or 2. Increment `fallback_count` for import failure, exception, non-solved status, or missing result vector. Keep returning safe zero commands on failure, but make that path observable. `reset()` resets counts/status while retaining backend/version.

- [ ] **Step 5: Implement exactly one E5 trial per CLI call**

Move aggregation out of the harness. `run_precision_trial` must select one condition, derive its target and disturbance, instantiate one controller, simulate one trial, and return:

```python
{
    "outcome": "success" if result.success else "failure",
    "failure_reason": "" if result.success else "controller_timeout",
    "metrics": {
        "success": result.success,
        "final_position_error": result.final_position_error,
        "final_yaw_error": result.final_yaw_error,
        "settling_time_s": result.settling_time_s,
        "effort_abs": result.effort_abs,
        "effort_sq": result.effort_sq,
        "constraint_violations": result.constraint_violations,
        "steps": result.steps,
    },
    "diagnostics": {
        "disturbance_sha256": disturbance_digest(disturbance),
        "solver_backend": controller.solver_backend if method == "MPC" else "none",
        "solver_version": controller.solver_version if method == "MPC" else "",
        "last_solver_status": controller.last_solver_status if method == "MPC" else "not_applicable",
        "solve_count": controller.solve_count if method == "MPC" else 0,
        "fallback_count": controller.fallback_count if method == "MPC" else 0,
        "solver_times_ms": result.solver_times_ms if method == "MPC" else [],
    },
    "run_id": None,
    "artifact_paths": [],
}
```

The CLI is:

```bash
python3 -m siminspect_benchmark.e5_trial \
  --method MPC --scenario F00 --condition E5_measurement_noise --seed 21 \
  --artifact-root artifacts/runs --require-osqp \
  --output /tmp/e5-harness.json
```

`--require-osqp` exits non-zero unless backend is OSQP, `solve_count > 0`, and `fallback_count == 0`. The release runner always passes this flag for MPC.

- [ ] **Step 6: Run unit tests and a real Ubuntu OSQP smoke**

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_e5_trial.py \
  src/siminspect_precision_control/test/test_mpc_controller.py -vv
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -m siminspect_benchmark.e5_trial \
  --method MPC --scenario F00 --condition E5_nominal --seed 21 \
  --artifact-root artifacts/runs --require-osqp \
  --output /tmp/e5-osqp-smoke.json
python3 -c 'import json; d=json.load(open("/tmp/e5-osqp-smoke.json")); assert d["diagnostics"]["solver_backend"]=="osqp"; assert d["diagnostics"]["solve_count"]>0; assert d["diagnostics"]["fallback_count"]==0'
```

Expected: all tests pass; the smoke proves a real OSQP solve and zero fallback.

- [ ] **Step 7: Install and commit the E5 harness**

Add `e5_trial.py` to `install(PROGRAMS ...)` and register `test_e5_trial` in CMake, then:

```bash
git add src/siminspect_benchmark/siminspect_benchmark/e5_trial.py \
  src/siminspect_benchmark/siminspect_benchmark/run_precision_benchmark.py \
  src/siminspect_precision_control/siminspect_precision_control/mpc_controller.py \
  src/siminspect_benchmark/test/test_e5_trial.py \
  src/siminspect_precision_control/test/test_mpc_controller.py \
  src/siminspect_benchmark/CMakeLists.txt
git commit -m "feat: verify paired PID and OSQP MPC trials"
```

### Task 6: Enforce exact-batch paired completeness

**Files:**
- Create: `src/siminspect_benchmark/siminspect_benchmark/validate_release_data.py`
- Create: `src/siminspect_benchmark/test/test_release_validation.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:6-24`

**Interfaces:**
- Produces: `collect_batch_records(raw_root, commit, batch_id) -> list[tuple[Path, dict]]`.
- Produces: `validate_release_batch(records, expected_specs, commit, batch_id) -> ValidationReport`.
- `ValidationReport` fields: expected, completed, outcome_failed, infrastructure_failed, missing, duplicate, unexpected, invalid, complete_pairs, incomplete_pairs, dirty_records, commit_mismatches, mpc_fallback_trials, pair_contract_mismatches.
- CLI exits 0 only when strict validation has no blocking field.
- Required by: Tasks 7-8 and Plan 04.

- [ ] **Step 1: Write failing strict-validation tests**

Create `test_release_validation.py` with fixture helpers that build schema-v2 records, then assert:

```python
def test_missing_one_assignment_blocks_release(tmp_path):
    matrix = load_release_matrix(MATRIX_PATH)
    expected = iter_release_trials(matrix, "development")
    records = [_record(spec) for spec in expected[:-1]]
    report = validate_release_batch(records, expected, "1" * 40, "dev-a")
    assert len(report.missing) == 1
    assert report.accepted is False


def test_completed_outcome_failure_remains_in_denominator():
    specs = [
        TrialSpec("E4", "B0", "F00", "mission", 21),
        TrialSpec("E4", "P2", "F00", "mission", 21),
    ]
    records = [_record(specs[0], outcome="failure"), _record(specs[1])]
    report = validate_release_batch(records, specs, "1" * 40, "dev-a")
    assert report.completed == 2
    assert report.outcome_failed == 1
    assert report.complete_pairs == 1
    assert report.accepted is True


def test_infrastructure_failure_is_preserved_and_blocks_release():
    spec = TrialSpec("E4", "B0", "F00", "mission", 21)
    report = validate_release_batch(
        [_record(spec, execution_status="infrastructure_failed", outcome=None)],
        [spec], "1" * 40, "dev-a",
    )
    assert report.infrastructure_failed == 1
    assert report.accepted is False


def test_e5_pair_requires_identical_disturbance_digest():
    specs = [
        TrialSpec("E5", "PID", "F00", "E5_measurement_noise", 21),
        TrialSpec("E5", "MPC", "F00", "E5_measurement_noise", 21),
    ]
    records = [
        _record(specs[0], diagnostics={"disturbance_sha256": "a" * 64,
                                      "solver_backend": "none", "fallback_count": 0}),
        _record(specs[1], diagnostics={"disturbance_sha256": "b" * 64,
                                      "solver_backend": "osqp", "solve_count": 2,
                                      "fallback_count": 0}),
    ]
    report = validate_release_batch(records, specs, "1" * 40, "dev-a")
    assert report.pair_contract_mismatches
    assert report.accepted is False


def test_mpc_fallback_blocks_release():
    spec = TrialSpec("E5", "MPC", "F00", "E5_nominal", 21)
    record = _record(spec, diagnostics={
        "disturbance_sha256": "a" * 64,
        "solver_backend": "osqp",
        "solve_count": 1,
        "fallback_count": 1,
    })
    report = validate_release_batch([record], [spec], "1" * 40, "dev-a")
    assert report.mpc_fallback_trials == 1
    assert report.accepted is False
```

The fixture must also cover duplicate paths, unexpected assignments, another commit, dirty provenance, and invalid required metrics.

- [ ] **Step 2: Run tests and confirm the validator is absent**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_release_validation.py -vv
```

Expected: FAIL while importing `validate_release_data`.

- [ ] **Step 3: Implement strict set and pair validation**

Use `TrialSpec` as the assignment identity. Do not use an intersection that silently drops missing pairs. Build:

```python
expected_set = set(expected_specs)
actual_by_spec: dict[TrialSpec, list[dict]] = defaultdict(list)
```

For every record, reconstruct the `TrialSpec`, validate schema/metrics, and append it. Report duplicates when a spec has more than one record in the selected batch. A pair is complete only when its exact required method set exists:

```python
required_methods = {"E4": {"B0", "P2"}, "E5": {"PID", "MPC"}}
```

For E4 pairs require equal `mission_id`, `world`, `config_sha256`, and scenario/seed. For E5 pairs require equal `target`, `dt`, `max_steps`, bounds digest, and `disturbance_sha256`. For every MPC record require backend `osqp`, `solve_count > 0`, and `fallback_count == 0`.

The CLI is:

```bash
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" --strict
```

Print these exact final-pool lines:

```text
E4 records=60 pairs=30
E5 records=100 pairs=50
total records=160 pairs=80
missing=0 duplicate=0 unexpected=0 infrastructure_failed=0
mpc_fallback_trials=0 pair_contract_mismatches=0
```

- [ ] **Step 4: Install and run all strict-validation tests**

Add `validate_release_data.py` to `install(PROGRAMS ...)`, register:

```cmake
ament_add_pytest_test(test_release_validation test/test_release_validation.py)
```

Run:

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_release_matrix.py \
  src/siminspect_benchmark/test/test_trial_schema.py \
  src/siminspect_benchmark/test/test_release_validation.py -vv
```

Expected: all tests pass; a one-record deletion fixture fails strict acceptance.

- [ ] **Step 5: Commit strict paired validation**

```bash
git add src/siminspect_benchmark/siminspect_benchmark/validate_release_data.py \
  src/siminspect_benchmark/test/test_release_validation.py \
  src/siminspect_benchmark/CMakeLists.txt
git commit -m "feat: enforce complete paired release data"
```

### Task 7: Generate deterministic raw-only summaries, claims, and plots

**Files:**
- Create: `src/siminspect_benchmark/siminspect_benchmark/build_release_results.py`
- Create: `src/siminspect_benchmark/test/test_release_results.py`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/analysis_core.py:115-191`
- Modify: `src/siminspect_benchmark/siminspect_benchmark/generate_plots.py:18-136`
- Modify: `src/siminspect_benchmark/CMakeLists.txt:6-26`
- Create after an accepted final-pool batch: `results/release/v0.1.0/summary.json`
- Create after an accepted final-pool batch: `results/release/v0.1.0/claims.json`
- Create after an accepted final-pool batch: `results/release/v0.1.0/provenance.json`
- Create after an accepted final-pool batch: `results/release/v0.1.0/raw_checksums.json`
- Create after an accepted final-pool batch: `results/release/v0.1.0/plots/viewpoint-success-by-scenario.svg`
- Create after an accepted final-pool batch: `results/release/v0.1.0/plots/viewpoint-cost-and-reinspection.svg`
- Create after an accepted final-pool batch: `results/release/v0.1.0/plots/precision-control-comparison.svg`
- Create after an accepted final-pool batch: `results/release/v0.1.0/plots/matrix-coverage.svg`

**Interfaces:**
- Consumes: one strictly accepted commit/batch and the exact expected final assignments.
- Produces: `build_release_summary(records, expected_specs) -> dict` with experiment -> scenario/condition -> method layers.
- Produces: `build_claims(summary, release, summary_sha256, git_commit, raw_prefix) -> dict`; every value includes bilingual labels, a JSON Pointer into `summary.json`, and the batch-scoped raw glob that supports it.
- Produces: deterministic UTF-8 JSON with sorted keys, no NaN, and one trailing newline.
- Produces: four headless SVG plots from `summary.json`; never reads the old top-level precision files.
- Required by: Task 8 and Plan 04.

- [ ] **Step 1: Write failing raw-only and determinism tests**

Create `test_release_results.py` with synthetic complete assignments and assert:

```python
def test_failed_outcome_is_in_success_rate_denominator():
    records = [
        _e4_record("B0", 1, outcome="failure"),
        _e4_record("B0", 2, outcome="success"),
    ]
    summary = build_release_summary(records, [record_spec(r) for r in records])
    node = summary["experiments"]["E4"]["scenarios"]["F00"]["methods"]["B0"]
    assert node["n"] == 2
    assert node["success_rate"] == 0.5


def test_summary_keeps_scenario_and_condition_layers():
    summary = build_release_summary(_complete_records(), _complete_specs())
    assert set(summary["experiments"]["E4"]["scenarios"]) == {"F00", "F06", "F07"}
    assert set(summary["experiments"]["E5"]["conditions"]) == {
        "E5_nominal", "E5_yaw_error", "E5_measurement_noise",
        "E5_wheel_slip", "E5_saturation",
    }


def test_claim_values_resolve_to_summary_json_pointers():
    summary = build_release_summary(_complete_records(), _complete_specs())
    claims = build_claims(
        summary, "v0.1.0", "a" * 64, "b" * 40,
        "experiments/raw/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/final_001",
    )
    assert 3 <= len(claims["claims"]) <= 5
    for claim in claims["claims"]:
        assert resolve_json_pointer(summary, claim["json_pointer"]) == claim["value"]
        assert claim["label_en"] and claim["label_zh"]
        assert claim["raw_glob"].startswith("experiments/raw/")


def test_result_build_is_byte_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_release_outputs(_complete_records(), _complete_specs(), first)
    build_release_outputs(_complete_records(), _complete_specs(), second)
    for relative in ("summary.json", "claims.json", "raw_checksums.json"):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_changing_raw_metric_changes_summary(tmp_path):
    records = _complete_records()
    first = build_release_summary(records, _complete_specs())
    records[0]["metrics"]["path_length_m"] += 1.0
    second = build_release_summary(records, _complete_specs())
    assert first != second


def test_four_release_plots_are_headless_and_nonempty(tmp_path):
    summary = build_release_summary(_complete_records(), _complete_specs())
    made = make_release_plots(summary, tmp_path)
    assert set(made) == {
        "viewpoint-success-by-scenario.svg",
        "viewpoint-cost-and-reinspection.svg",
        "precision-control-comparison.svg",
        "matrix-coverage.svg",
    }
    assert all((tmp_path / name).stat().st_size > 1000 for name in made)
```

- [ ] **Step 2: Run tests and verify the release builder is absent**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_release_results.py -vv
```

Expected: FAIL while importing `build_release_results`.

- [ ] **Step 3: Implement stratified summaries and neutral claims**

Aggregate E4 separately by scenario/method and E5 separately by condition/method. Preserve `n`, `outcome_failure_count`, and all means. Calculate paired deltas from exact pair keys, never by truncating unequal arrays. Emit 3-5 neutral claims without implying improvement:

```json
{
  "schema_version": "1.0",
  "release": "v0.1.0",
  "source": {
    "summary": "summary.json",
    "sha256": "64 lowercase hexadecimal characters",
    "git_commit": "40 lowercase hexadecimal characters"
  },
  "claims": [
    {
      "id": "e4_b0_valid_read_rate",
      "label_en": "B0 valid-read rate",
      "label_zh": "B0 有效读数率",
      "value": 0.0,
      "unit": "ratio",
      "json_pointer": "/experiments/E4/overall/methods/B0/valid_read_rate",
      "raw_glob": "experiments/raw/*/*/E4_viewpoint_policy/B0/*/mission/*.json"
    },
    {
      "id": "e4_p2_valid_read_rate",
      "label_en": "P2 valid-read rate",
      "label_zh": "P2 有效读数率",
      "value": 0.0,
      "unit": "ratio",
      "json_pointer": "/experiments/E4/overall/methods/P2/valid_read_rate",
      "raw_glob": "experiments/raw/*/*/E4_viewpoint_policy/P2/*/mission/*.json"
    },
    {
      "id": "e4_p2_minus_b0_valid_read_rate",
      "label_en": "P2 minus B0 valid-read rate",
      "label_zh": "P2 相对 B0 的有效读数率差",
      "value": 0.0,
      "unit": "percentage_points",
      "json_pointer": "/experiments/E4/paired/P2_minus_B0/valid_read_rate_percentage_points",
      "raw_glob": "experiments/raw/*/*/E4_viewpoint_policy/*/*/mission/*.json"
    },
    {
      "id": "e5_pid_mean_position_error",
      "label_en": "PID mean final position error",
      "label_zh": "PID 平均最终位置误差",
      "value": 0.0,
      "unit": "m",
      "json_pointer": "/experiments/E5/overall/methods/PID/mean_final_position_error",
      "raw_glob": "experiments/raw/*/*/E5_precision_control/PID/F00/*/*.json"
    },
    {
      "id": "e5_mpc_mean_position_error",
      "label_en": "MPC mean final position error",
      "label_zh": "MPC 平均最终位置误差",
      "value": 0.0,
      "unit": "m",
      "json_pointer": "/experiments/E5/overall/methods/MPC/mean_final_position_error",
      "raw_glob": "experiments/raw/*/*/E5_precision_control/MPC/F00/*/*.json"
    }
  ]
}
```

The numeric zeros above describe the schema shape only; `build_claims` must replace every value by resolving its pointer from the computed summary and must raise if any pointer is missing. It must hash the canonical `summary.json`, fill the exact 40-character evaluated commit, and narrow every `raw_glob` to the selected commit and batch before writing `claims.json`.

- [ ] **Step 4: Make release plots deterministic and headless**

Use:

```python
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "siminspect-x-v0.1.0"
```

Save SVGs with `metadata={"Date": None}`. The coverage plot shows expected vs completed per experiment and must display 60/60 and 100/100 for an accepted final batch. Remove the release path's ablation plot; ablations are outside this product-release matrix.

- [ ] **Step 5: Implement the strict result CLI**

The CLI must first call the strict validator and refuse output on failure:

```bash
ros2 run siminspect_benchmark build_release_results \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" \
  --version v0.1.0 --output results/release/v0.1.0
```

Write outputs to a temporary sibling directory and atomically rename it only after all JSON and plots succeed. `provenance.json` records the evaluated source commit, batch ID, matrix/config hashes, raw record count, and generated UTC time; public exact-tag binding remains the external release index in Plan 04 to avoid a commit self-reference.

- [ ] **Step 6: Run focused tests twice**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_release_results.py -vv
python3 -m pytest src/siminspect_benchmark/test/test_release_results.py -vv
```

Expected: both runs pass; deterministic file comparisons pass.

- [ ] **Step 7: Install and commit the result pipeline**

Add `build_release_results.py` to `install(PROGRAMS ...)` and register `test_release_results`, then:

```bash
git add src/siminspect_benchmark/siminspect_benchmark/build_release_results.py \
  src/siminspect_benchmark/siminspect_benchmark/analysis_core.py \
  src/siminspect_benchmark/siminspect_benchmark/generate_plots.py \
  src/siminspect_benchmark/test/test_release_results.py \
  src/siminspect_benchmark/CMakeLists.txt
git commit -m "feat: regenerate deterministic release results"
```

### Task 8: Pass the 48-record development gate and freeze behavior

**Files:**
- Create outside Git: `experiments/raw/$COMMIT/$DEVELOPMENT_BATCH_ID/batch_manifest.json`
- Create outside Git: 18 E4 development records.
- Create outside Git: 30 E5 development records.
- Create outside Git: `artifacts/validation/$DEVELOPMENT_BATCH_ID/gate-d-development.log`

**Interfaces:**
- Consumes: clean committed Tasks 1-7, accepted F06/F07 behavior, and Ubuntu OSQP.
- Produces: one strictly accepted development batch with 48 records and 24 pairs.
- Freezes: viewpoint parameters, controller parameters, fault parameters, timeouts, targets, metrics, and release matrix before any final seed is used.
- Required by: Task 9.

- [ ] **Step 1: Verify prerequisites and a clean commit**

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
test -z "$(git status --porcelain)"
DEV_SHA="$(git rev-parse HEAD)"
python3 -c 'import osqp; print(osqp.__version__)'
./run_demo.sh --headless --benchmark-evidence --method P2 --scenario F06 --seed 21 --artifact-root artifacts/runs
./run_demo.sh --headless --benchmark-evidence --method P2 --scenario F07 --seed 21 --artifact-root artifacts/runs
```

Expected: the worktree is clean; F06 proves the spawned occluder; F07 proves modified camera frames, a low-confidence read, and a distinct alternative-viewpoint attempt.

- [ ] **Step 2: Run all 18 development E4 records**

```bash
DEV_BATCH="dev-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "artifacts/validation/$DEV_BATCH"
ros2 run siminspect_benchmark run_seed_sweep \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool development --batch-id "$DEV_BATCH" --commit "$DEV_SHA" \
  --raw-root experiments/raw --artifact-root artifacts/runs \
  --experiments E4 --methods B0 P2 --scenarios F00 F06 F07 \
  --seeds 21 22 23 \
  2>&1 | tee "artifacts/validation/$DEV_BATCH/e4.log"
```

Expected: `expected=18 completed=18 infrastructure_failed=0`.

- [ ] **Step 3: Add all 30 development E5 records to the same batch**

The sweep must support appending disjoint assignments to an existing batch only when commit, matrix checksum, pool, and configuration hashes match and no destination record exists:

```bash
ros2 run siminspect_benchmark run_seed_sweep \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool development --batch-id "$DEV_BATCH" --commit "$DEV_SHA" \
  --raw-root experiments/raw --artifact-root artifacts/runs \
  --experiments E5 --methods PID MPC \
  --conditions E5_nominal E5_yaw_error E5_measurement_noise \
               E5_wheel_slip E5_saturation \
  --seeds 21 22 23 \
  2>&1 | tee "artifacts/validation/$DEV_BATCH/e5.log"
```

Expected: `expected=30 completed=30 infrastructure_failed=0` and every MPC trial reports a real OSQP backend with zero fallback.

- [ ] **Step 4: Strictly validate the complete 48-record batch**

```bash
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool development --raw-root experiments/raw \
  --commit "$DEV_SHA" --batch-id "$DEV_BATCH" --strict \
  2>&1 | tee "artifacts/validation/$DEV_BATCH/gate-d-development.log"
```

Expected:

```text
E4 records=18 pairs=9
E5 records=30 pairs=15
total records=48 pairs=24
missing=0 duplicate=0 unexpected=0 infrastructure_failed=0
mpc_fallback_trials=0 pair_contract_mismatches=0
```

- [ ] **Step 5: Freeze the implementation before final seeds**

```bash
test -z "$(git status --porcelain)"
git rev-parse HEAD
sha256sum \
  src/siminspect_benchmark/config/release_matrix.yaml \
  src/siminspect_benchmark/config/fault_scenarios.yaml \
  src/siminspect_benchmark/config/precision_benchmark.yaml \
  config/demo_config.yaml \
  | tee "artifacts/validation/$DEV_BATCH/frozen-config.sha256"
```

If any development finding requires a code or configuration change, make that surgical change with a reproducing test, commit it, and repeat all of Task 8 under a new batch ID. Do not run seed 1-10 until the 48-record batch for the current commit passes unchanged.

### Task 9: Run the 160-record final pool and generate candidate release outputs

**Files:**
- Create outside Git: `experiments/raw/$COMMIT/$FINAL_BATCH_ID/batch_manifest.json`
- Create outside Git: 60 E4 final records.
- Create outside Git: 100 E5 final records.
- Create outside Git: `artifacts/validation/$FINAL_BATCH_ID/gate-d-final.log`
- Create: `results/release/v0.1.0/summary.json`
- Create: `results/release/v0.1.0/claims.json`
- Create: `results/release/v0.1.0/provenance.json`
- Create: `results/release/v0.1.0/raw_checksums.json`
- Create: `results/release/v0.1.0/plots/*.svg`

**Interfaces:**
- Consumes: the exact clean commit that passed Task 8 without parameter changes.
- Produces: 160 completed records, 80 complete pairs, zero infrastructure failure, zero MPC fallback, deterministic candidate release outputs.
- Required by: Plan 04, which reruns Gates A-D on the eventual release commit before publishing.

- [ ] **Step 1: Bind the final batch to the frozen clean commit**

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
test -z "$(git status --porcelain)"
RC_SHA="$(git rev-parse HEAD)"
FINAL_BATCH="final-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "artifacts/validation/$FINAL_BATCH"
```

Expected: `RC_SHA` equals the commit that passed the development gate. If it differs, rerun Task 8 first.

- [ ] **Step 2: Run all 60 E4 final records**

```bash
ros2 run siminspect_benchmark run_seed_sweep \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --batch-id "$FINAL_BATCH" --commit "$RC_SHA" \
  --raw-root experiments/raw --artifact-root artifacts/runs \
  --experiments E4 --methods B0 P2 --scenarios F00 F06 F07 \
  --seeds 1 2 3 4 5 6 7 8 9 10 \
  2>&1 | tee "artifacts/validation/$FINAL_BATCH/e4.log"
```

Expected: `expected=60 completed=60 infrastructure_failed=0`. Outcome failures are retained and do not abort the sweep.

- [ ] **Step 3: Run all 100 E5 final records**

```bash
ros2 run siminspect_benchmark run_seed_sweep \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --batch-id "$FINAL_BATCH" --commit "$RC_SHA" \
  --raw-root experiments/raw --artifact-root artifacts/runs \
  --experiments E5 --methods PID MPC \
  --conditions E5_nominal E5_yaw_error E5_measurement_noise \
               E5_wheel_slip E5_saturation \
  --seeds 1 2 3 4 5 6 7 8 9 10 \
  2>&1 | tee "artifacts/validation/$FINAL_BATCH/e5.log"
```

Expected: `expected=100 completed=100 infrastructure_failed=0`; 50 MPC records each show OSQP solves and zero fallback.

- [ ] **Step 4: Strictly validate Gate D**

```bash
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" --strict \
  2>&1 | tee "artifacts/validation/$FINAL_BATCH/gate-d-final.log"
```

Expected exactly:

```text
E4 records=60 pairs=30
E5 records=100 pairs=50
total records=160 pairs=80
missing=0 duplicate=0 unexpected=0 infrastructure_failed=0
mpc_fallback_trials=0 pair_contract_mismatches=0
```

- [ ] **Step 5: Generate release outputs twice and compare them**

```bash
VERIFY_DIR="$(mktemp -d)"
ros2 run siminspect_benchmark build_release_results \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" \
  --version v0.1.0 --output results/release/v0.1.0
ros2 run siminspect_benchmark build_release_results \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" \
  --version v0.1.0 --output "$VERIFY_DIR"
diff -u results/release/v0.1.0/summary.json "$VERIFY_DIR/summary.json"
diff -u results/release/v0.1.0/claims.json "$VERIFY_DIR/claims.json"
diff -u results/release/v0.1.0/raw_checksums.json "$VERIFY_DIR/raw_checksums.json"
```

Expected: all diffs are empty. Plot existence and content are covered by the release-result tests; generated timestamps belong only in `provenance.json` and are excluded from byte-equality comparison.

- [ ] **Step 6: Run the complete engineering test gate**

```bash
python3 -m pytest \
  src/siminspect_benchmark/test/test_release_matrix.py \
  src/siminspect_benchmark/test/test_trial_schema.py \
  src/siminspect_benchmark/test/test_experiment_runner.py \
  src/siminspect_benchmark/test/test_e4_trial.py \
  src/siminspect_benchmark/test/test_e5_trial.py \
  src/siminspect_benchmark/test/test_release_validation.py \
  src/siminspect_benchmark/test/test_release_results.py -vv
colcon test --packages-select \
  siminspect_benchmark siminspect_precision_control \
  --return-code-on-test-failure
colcon test-result --all --verbose
```

Expected: all tests pass and `colcon test-result` reports zero failures.

- [ ] **Step 7: Confirm raw data stayed untracked and commit only curated outputs**

```bash
git status --short
git check-ignore experiments/raw/"$RC_SHA"/"$FINAL_BATCH"/batch_manifest.json
git add results/release/v0.1.0
git commit -m "results: add representative evaluation evidence"
```

Expected: no file under `experiments/raw/` or `artifacts/` is staged. `provenance.json` identifies `RC_SHA` and `FINAL_BATCH` as the candidate data source. Plan 04 must rerun the complete matrix on the eventual public release commit and bind that final raw archive through the external release evidence index.

## Plan Acceptance

Run on Ubuntu 24.04 after Tasks 1-9:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --pool final --raw-root experiments/raw \
  --commit "$RC_SHA" --batch-id "$FINAL_BATCH" --strict
python3 -m pytest \
  src/siminspect_benchmark/test/test_release_matrix.py \
  src/siminspect_benchmark/test/test_trial_schema.py \
  src/siminspect_benchmark/test/test_experiment_runner.py \
  src/siminspect_benchmark/test/test_e4_trial.py \
  src/siminspect_benchmark/test/test_e5_trial.py \
  src/siminspect_benchmark/test/test_release_validation.py \
  src/siminspect_benchmark/test/test_release_results.py -q
colcon test --packages-select siminspect_benchmark siminspect_precision_control \
  --return-code-on-test-failure
colcon test-result --all --verbose
test -f results/release/v0.1.0/summary.json
test -f results/release/v0.1.0/claims.json
test "$(find results/release/v0.1.0/plots -maxdepth 1 -name '*.svg' | wc -l)" -eq 4
```

Accept this plan only when the selected final batch reports 60 E4 records/30 pairs and 100 E5 records/50 pairs, has no missing/duplicate/unexpected/infrastructure-failed record, has no MPC fallback or pair-contract mismatch, preserves all experimental failures in the raw dataset, and regenerates the committed candidate summary and plots exclusively from that batch. Do not begin public numeric README claims before this gate passes.
