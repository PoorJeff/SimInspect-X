# GitHub Product Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish SimInspect-X v0.1.0 as an English-primary, Chinese-secondary GitHub product release whose media, claims, diagrams, governance, and downloadable evidence are reproducible and traceable to accepted runs on the release commit.

**Architecture:** Treat the repository as the small, reviewable product surface and GitHub Release assets as the large evidence surface. Repository claims are generated from `claims.json`; accepted-run media is promoted only after checksum and acceptance checks; deterministic bundles and a post-publish external index bind the final tag SHA without creating a commit self-reference.

**Tech Stack:** Python 3, pytest, JSON, Markdown, SVG, Pillow, ffmpeg/ffprobe, tar, gzip, SHA-256, Git, GitHub Actions, GitHub CLI.

## Global Constraints

- Gate E consumes Gate A-D evidence from the same clean release commit; until all gates pass, status is exactly `implementation complete; runtime validation in progress`.
- Ground truth is benchmark-only and never an autonomy input; diagrams and copy must preserve that firewall.
- Public numbers come only from `results/release/v0.1.0/claims.json`, whose JSON pointers resolve into its raw-derived `summary.json`.
- English and Chinese READMEs contain equivalent commands, status, claim IDs, limitations, and evidence links; English remains primary.
- Only media from an accepted live run may enter `docs/media/`; full MP4 and raw archives remain GitHub Release assets.
- Failed trials remain in the raw bundle; deterministic packaging must not filter records by outcome.
- Do not claim physical deployment, a real synchronized digital twin, calibrated confidence, or validation of all F00-F11 scenarios.
- Repository-generated SVG is committed together with its generator; external reuse requires source, version, license, copied files, and modifications.
- The release version and annotated tag are exactly `v0.1.0`.

---

## File Structure

- `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md` — public governance and attribution.
- `.github/ISSUE_TEMPLATE/*` and `.github/pull_request_template.md` — bounded support and contribution intake.
- `docs/architecture/generate_diagrams.py` plus three SVG files — reproducible architecture, mission flow, and firewall visuals.
- `scripts/publish_demo_media.py` — accepted-run verifier and deterministic GIF/hero publisher.
- `scripts/render_release_claims.py` — validates claim pointers and replaces bounded README claim regions.
- `scripts/build_release_bundle.py` — deterministic evidence/raw archives and checksums.
- `scripts/validate_public_release.py` — Gate E repository validator.
- `scripts/publish_github_release.py` — creates the post-publish external evidence index.
- `docs/demo/*`, `docs/validation/*`, `docs/media/*`, `README.md`, `README.zh-CN.md` — product and evidence surface.
- `src/siminspect_benchmark/test/test_public_release.py` and `test_release_bundle.py` — pure release contracts registered in CMake.

### Task 1: Add governance, attribution, and data hygiene

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/pull_request_template.md`
- Modify: `docs/SOURCE_MANIFEST.json`
- Modify: `third_party/README.md`
- Modify: `.gitignore`
- Test: `src/siminspect_benchmark/test/test_public_release.py`

**Interfaces:**
- Consumes: existing package manifests and `docs/SOURCE_MANIFEST.json` sources.
- Produces: `load_source_manifest(path: Path) -> dict` and a complete root-level governance contract.

- [ ] **Step 1: Write failing governance tests**

```python
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]

def test_governance_and_source_records():
    for name in ("LICENSE", "CONTRIBUTING.md", "SECURITY.md",
                 "THIRD_PARTY_NOTICES.md"):
        assert (ROOT / name).is_file()
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    data = json.loads((ROOT / "docs/SOURCE_MANIFEST.json").read_text())
    assert data["schema_version"] == "1.0"
    for item in data["sources"]:
        assert set(("title", "source", "version", "license", "role",
                    "copied_files", "modifications")) <= item.keys()

def test_large_outputs_are_ignored_but_curated_outputs_are_allowed():
    rules = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for rule in ("artifacts/runs/", "artifacts/release/", "*.mp4",
                 "*.tar.gz"):
        assert rule in rules
    assert "!docs/media/" in rules and "!results/release/" in rules
```

- [ ] **Step 2: Prove the tests fail before adding files**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_public_release.py -vv`

Expected: FAIL naming the missing root governance files or incomplete source records.

- [ ] **Step 3: Add exact governance and attribution content**

Use the standard MIT text in `LICENSE` with `Copyright (c) 2026 SimInspect-X contributors`. `CONTRIBUTING.md` must require Ubuntu 24.04, `./scripts/verify_foundation.sh`, focused changes, paired seeds, retained failures, and attribution review. `SECURITY.md` must request private GitHub security reports, define supported version `v0.1.x`, and forbid secrets in issues. `THIRD_PARTY_NOTICES.md` must state that the plant, robot geometry, gauge artwork, diagrams, and demo media are repository-generated unless an item in `docs/SOURCE_MANIFEST.json` says otherwise.

Replace the source manifest with schema `1.0`, retaining each current URL and adding the seven required fields. Record references as `copied_files: []`; never label conceptual inspiration as copied code. Add the four ignore rules above, retain `experiments/raw/*`, and add allow rules for `docs/media/` and `results/release/`.

- [ ] **Step 4: Run governance tests and validate JSON**

```bash
python3 -m json.tool docs/SOURCE_MANIFEST.json >/dev/null
python3 -m pytest src/siminspect_benchmark/test/test_public_release.py -vv
```

Expected: PASS.

- [ ] **Step 5: Commit governance**

```bash
git add LICENSE CONTRIBUTING.md SECURITY.md THIRD_PARTY_NOTICES.md .gitignore \
  .github/ISSUE_TEMPLATE .github/pull_request_template.md \
  docs/SOURCE_MANIFEST.json third_party/README.md \
  src/siminspect_benchmark/test/test_public_release.py
git commit -m "docs: add release governance and attribution"
```

### Task 2: Generate the public SVG architecture set

**Files:**
- Create: `docs/architecture/README.md`
- Create: `docs/architecture/generate_diagrams.py`
- Create: `docs/architecture/system-overview.svg`
- Create: `docs/architecture/mission-data-flow.svg`
- Create: `docs/architecture/ground-truth-firewall.svg`
- Modify: `src/siminspect_benchmark/test/test_public_release.py`

**Interfaces:**
- Consumes: contracts in `docs/03_SYSTEM_ARCHITECTURE.md` and `docs/06_ROS_TF_CONTRACT.md`.
- Produces: `render_all(output_dir: Path) -> list[Path]`, sorted as the three filenames above.

- [ ] **Step 1: Add failing deterministic-diagram tests**

```python
import hashlib
import subprocess
import sys

def test_architecture_diagrams_are_regenerable(tmp_path):
    script = ROOT / "docs/architecture/generate_diagrams.py"
    subprocess.run([sys.executable, str(script), "--output-dir", str(tmp_path)],
                   check=True)
    names = ("system-overview.svg", "mission-data-flow.svg",
             "ground-truth-firewall.svg")
    for name in names:
        generated = (tmp_path / name).read_bytes()
        committed = (ROOT / "docs/architecture" / name).read_bytes()
        assert hashlib.sha256(generated).digest() == hashlib.sha256(committed).digest()
    firewall = (tmp_path / names[2]).read_text(encoding="utf-8")
    assert "benchmark-only" in firewall and "autonomy" in firewall
```

- [ ] **Step 2: Run the test and observe the missing generator**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_public_release.py::test_architecture_diagrams_are_regenerable -vv`

Expected: FAIL because `generate_diagrams.py` does not exist.

- [ ] **Step 3: Implement a deterministic standard-library SVG renderer**

Define `svg_document(title: str, boxes: list[dict], edges: list[dict]) -> str` and fixed node/edge lists. `system-overview.svg` must show Gazebo/sensors -> EKF/SLAM/Nav2 -> viewpoint -> precision -> vision -> mission -> evidence. `mission-data-flow.svg` must show navigate, select, align, read, alternative-viewpoint re-inspection, return home, and report. `ground-truth-firewall.svg` must place `/benchmark_ground_truth/*` inside a red `benchmark-only` boundary with no edge into autonomy. Sort attributes and end every output with one newline; do not embed timestamps or machine paths.

- [ ] **Step 4: Generate twice and prove byte identity**

```bash
python3 docs/architecture/generate_diagrams.py --output-dir docs/architecture
cp docs/architecture/system-overview.svg /tmp/system-overview.svg
python3 docs/architecture/generate_diagrams.py --output-dir docs/architecture
cmp /tmp/system-overview.svg docs/architecture/system-overview.svg
python3 -m pytest src/siminspect_benchmark/test/test_public_release.py -vv
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit diagrams with their source**

```bash
git add docs/architecture src/siminspect_benchmark/test/test_public_release.py
git commit -m "docs: add reproducible product architecture diagrams"
```

### Task 3: Promote only accepted live-run media

**Files:**
- Create: `scripts/publish_demo_media.py`
- Create after an accepted run: `docs/media/hero.webp`
- Create after an accepted run: `docs/media/demo-preview.gif`
- Create after an accepted run: `docs/media/media-manifest.json`
- Test: `src/siminspect_benchmark/test/test_publish_demo_media.py`

**Interfaces:**
- Consumes: `artifacts/runs/$RUN_ID/acceptance.json`, `manifest.json`, `events.jsonl`, `media/index.json`, `media/demo.mp4`, and five fixed WebP screenshots.
- Produces: `publish(run_dir: Path, output_dir: Path, max_gif_seconds: float = 20.0) -> dict`; rejects unless `acceptance.overall == "passed"`, `manifest.git.dirty is false`, all source checksums match, and media items use `source: "live_capture"`.

- [ ] **Step 1: Write failure-first media tests**

```python
def test_rejects_failed_run(tmp_path):
    run = make_run_fixture(tmp_path, overall="failed")
    with pytest.raises(ValueError, match="accepted run required"):
        publish(run, tmp_path / "out")

def test_manifest_binds_curated_media_to_run(tmp_path, fake_ffmpeg):
    run = make_run_fixture(tmp_path, overall="passed")
    result = publish(run, tmp_path / "out", 20.0)
    assert result["run_id"] == run.name
    assert result["git_commit"] == "a" * 40
    assert [x["path"] for x in result["outputs"]] == [
        "demo-preview.gif", "hero.webp"]
```

The fixture must use the Plan 02 schemas: `manifest.git.commit_sha`, `acceptance.gates`, and `media/index.json` items with relative paths and SHA-256.

- [ ] **Step 2: Confirm rejection and missing implementation failures**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_publish_demo_media.py -vv`

Expected: FAIL because `scripts.publish_demo_media` is absent.

- [ ] **Step 3: Implement verification and event-driven ffmpeg selection**

Parse JSONL events and select `monotonic_s` for `navigation.started`, `viewpoint.selected`, `gauge.reading`, `reinspection.requested`, and `mission.return_home_completed`. Build five clips of at most four seconds each, concatenate them, then run:

```bash
ffmpeg -y -i preview.mp4 -vf "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" docs/media/demo-preview.gif
```

Copy `media/screenshots/05-mission-complete.webp` as `hero.webp`. Write `media-manifest.json` with schema `1.0`, run ID, full 40-character commit, source relative paths/checksums, output checksums, event names, and tool versions. Use `subprocess.run(..., check=True)`; partial outputs stay outside `docs/media/` until all validation succeeds.

- [ ] **Step 4: Run pure tests, then publish the accepted F07 run**

```bash
python3 -m pytest src/siminspect_benchmark/test/test_publish_demo_media.py -vv
F07_RUN_ID="${SIMINSPECT_F07_RUN_ID:?export the accepted Plan 02 F07 run ID}"
python3 scripts/publish_demo_media.py \
  --run-dir "artifacts/runs/$F07_RUN_ID" \
  --output docs/media --require-accepted --max-gif-seconds 20
python3 -m json.tool docs/media/media-manifest.json >/dev/null
```

Replace the run-directory example with the immutable accepted F07 run ID printed by Plan 02; the script itself verifies scenario `F07`, seed `21`, and re-inspection events before publishing.

- [ ] **Step 5: Commit curated media, never the MP4**

```bash
git add scripts/publish_demo_media.py docs/media \
  src/siminspect_benchmark/test/test_publish_demo_media.py
git commit -m "docs: publish accepted live demo media"
```

### Task 4: Render raw-derived claims and build bilingual product documentation

**Files:**
- Create: `scripts/render_release_claims.py`
- Create: `README.zh-CN.md`
- Create: `docs/demo/README.md`
- Create: `docs/demo/troubleshooting.md`
- Create: `docs/demo/mission_report.example.json`
- Create: `docs/validation/ACCEPTANCE.md`
- Create: `docs/validation/RESULTS.md`
- Create: `docs/validation/evidence-index.json`
- Modify: `README.md`
- Modify: `src/siminspect_benchmark/test/test_readme_structure.py`
- Modify: `src/siminspect_benchmark/test/test_public_release.py`

**Interfaces:**
- Consumes: `results/release/v0.1.0/{summary.json,claims.json,provenance.json,plots/}`, accepted run IDs, and media manifest.
- Produces: `load_claims(summary_path: Path, claims_path: Path) -> list[dict]` and `render_region(text: str, language: str, claims: list[dict]) -> str` between `<!-- release-claims:start -->` and `<!-- release-claims:end -->`.

- [ ] **Step 1: Add failing schema and bilingual-equivalence tests**

```python
def test_claims_resolve_to_summary():
    summary, claims = release_files("v0.1.0")
    for claim in load_claims(summary, claims):
        assert resolve_pointer(read_json(summary), claim["json_pointer"]) == claim["value"]
        assert claim["raw_glob"].startswith("experiments/raw/")

def test_readmes_share_public_contract():
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    for token in ("./run_demo.sh --headless", "./run_demo.sh --visual",
                  "./run_demo.sh --visual --record", "v0.1.0"):
        assert token in en and token in zh
    ids = [c["id"] for c in load_claims(*release_files("v0.1.0"))]
    assert all(f'data-claim-id="{cid}"' in en and f'data-claim-id="{cid}"' in zh
               for cid in ids)
```

- [ ] **Step 2: Run tests and confirm old README contracts fail**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_readme_structure.py src/siminspect_benchmark/test/test_public_release.py -vv`

Expected: FAIL because Chinese README, current diagrams, evidence index, and bounded claim regions are missing.

- [ ] **Step 3: Implement strict claim loading and rendering**

Require claims schema:

```json
{"schema_version":"1.0","release":"v0.1.0","source":{"summary":"summary.json","sha256":"64 lowercase hexadecimal characters","git_commit":"40 lowercase hexadecimal characters"},"claims":[{"id":"e4_p2_valid_read_rate","label_en":"P2 valid-read rate","label_zh":"P2 有效读数率","value":0.0,"unit":"ratio","json_pointer":"/experiments/E4/overall/methods/P2/valid_read_rate","raw_glob":"experiments/raw/40-character-commit/final-batch/E4_viewpoint_policy/P2/*/mission/*.json"}]}
```

The literal values above document types only; execution uses Plan 03 output unchanged. Reject duplicate IDs, source hash mismatch, non-resolving pointers, altered values, unknown units, or more than five claims. Format `ratio` as one decimal percent, seconds to two decimals, and metres to two decimals; write values only inside the bounded regions.

- [ ] **Step 4: Write the English product page and equivalent Chinese page**

Use this exact order in both: language switch/badges; one-sentence value; linked `docs/media/demo-preview.gif`; validated-capabilities table; seven-stage inspection loop; generated three-to-five-claim region; current diagrams; Docker quick start; visual/headless commands; reproducibility/evidence; limitations/non-claims; contribution/security/license. Remove primary links to `docs/report/*`, future-tense demo copy, and any implication that all F00-F11 conditions passed.

`docs/demo/README.md` documents the same three commands and accepted-run layout. `troubleshooting.md` covers Docker daemon, VM NAT, DISPLAY/X11, Nav2 readiness, Gazebo sensors, OSQP import, artifact permissions, and preserved failed runs. Copy an accepted report to `mission_report.example.json` and add `_provenance` containing run ID, commit, and source checksum without changing mission results.

Create `evidence-index.json` with `schema_version`, `release`, `status`, accepted `run_ids`, repository-relative `claims`, `raw_data`, `plots`, `logs`, `media`, and expected release asset names. It must not contain the index's own SHA or an exact tag commit. `RESULTS.md` is generated from claims; `ACCEPTANCE.md` maps Gates A-E to repository evidence.

- [ ] **Step 5: Render and verify deterministic README output**

```bash
python3 scripts/render_release_claims.py \
  --summary results/release/v0.1.0/summary.json \
  --claims results/release/v0.1.0/claims.json \
  --readme-en README.md --readme-zh README.zh-CN.md
git diff --exit-code -- README.md README.zh-CN.md docs/validation/RESULTS.md || true
python3 scripts/render_release_claims.py \
  --summary results/release/v0.1.0/summary.json \
  --claims results/release/v0.1.0/claims.json \
  --readme-en README.md --readme-zh README.zh-CN.md
git diff --exit-code -- README.md README.zh-CN.md docs/validation/RESULTS.md
python3 -m pytest src/siminspect_benchmark/test/test_readme_structure.py \
  src/siminspect_benchmark/test/test_public_release.py -vv
```

Expected: the second render produces no diff and all tests pass.

- [ ] **Step 6: Commit product documentation**

```bash
git add README.md README.zh-CN.md docs/demo docs/validation \
  scripts/render_release_claims.py src/siminspect_benchmark/test/test_readme_structure.py \
  src/siminspect_benchmark/test/test_public_release.py
git commit -m "docs: build bilingual evidence-backed product pages"
```

### Task 5: Build deterministic release bundles and validate Gate E

**Files:**
- Create: `scripts/build_release_bundle.py`
- Create: `scripts/validate_public_release.py`
- Create: `scripts/publish_github_release.py`
- Create at execution: `artifacts/release/v0.1.0/release-evidence.tar.gz`
- Create at execution: `artifacts/release/v0.1.0/release-raw-trials.tar.gz`
- Create at execution: `artifacts/release/v0.1.0/SHA256SUMS`
- Create after publication: `artifacts/release/v0.1.0/release-evidence-index.json`
- Create: `src/siminspect_benchmark/test/test_release_bundle.py`
- Modify: `src/siminspect_benchmark/CMakeLists.txt`

**Interfaces:**
- Consumes: clean release tree, accepted run manifests, 160 preserved raw records, public indexes, full demo MP4, and claims.
- Produces: `build_bundle(version: str, repo: Path, output: Path, source_date_epoch: int) -> list[Path]`, `validate_release(root: Path, version: str, strict: bool) -> list[str]`, and `build_external_index(tag: str, commit: str, assets: list[dict]) -> dict`.

- [ ] **Step 1: Write deterministic-archive and self-reference tests**

```python
def test_bundle_is_byte_deterministic(tmp_path, release_fixture):
    one = build_bundle("v0.1.0", release_fixture, tmp_path / "one", 0)
    two = build_bundle("v0.1.0", release_fixture, tmp_path / "two", 0)
    assert [sha256(p) for p in one] == [sha256(p) for p in two]

def test_two_layer_indexes_avoid_self_reference(release_fixture):
    repo_index = read_json(release_fixture / "docs/validation/evidence-index.json")
    assert "commit_sha" not in repo_index
    external = build_external_index("v0.1.0", "b" * 40, [asset_fixture()])
    assert external["git_commit"] == "b" * 40
    assert all(x["url"].startswith("https://github.com/PoorJeff/SimInspect-X/releases/download/v0.1.0/")
               for x in external["assets"])
```

- [ ] **Step 2: Run tests to verify missing release tools**

Run: `python3 -m pytest src/siminspect_benchmark/test/test_release_bundle.py -vv`

Expected: FAIL because the three scripts do not exist.

- [ ] **Step 3: Implement deterministic packaging**

Evidence bundle members are accepted manifests/reports/acceptance/log excerpts, `docs/validation`, `docs/media/media-manifest.json`, and `results/release/v0.1.0`. Raw bundle members are every file selected by the E4/E5 raw globs, including unsuccessful trials. Sort POSIX paths; set tar uid/gid to `0`, names to empty strings, mode to `0644`, mtime to `SOURCE_DATE_EPOCH`; write gzip with `filename=""` and that mtime. Write sorted `SHA256SUMS` lines as `SHA256_VALUE`, two spaces, then `RELATIVE_FILENAME`, and exclude `SHA256SUMS` from itself.

The strict validator checks: clean tree; exact version; all public links resolve locally; diagrams regenerate byte-identically; media source and output hashes; claim pointers and README regions; EN/ZH command/status/claim equivalence; no `pending` after Gates A-D pass; 60 E4 and 100 E5 records; failed records preserved; no MP4/raw archive tracked; governance files; and registered tests.

- [ ] **Step 4: Register and run all release tests**

Add these exact registrations under `BUILD_TESTING`:

```cmake
ament_add_pytest_test(test_public_release test/test_public_release.py)
ament_add_pytest_test(test_publish_demo_media test/test_publish_demo_media.py)
ament_add_pytest_test(test_release_bundle test/test_release_bundle.py)
ament_add_pytest_test(test_readme_structure test/test_readme_structure.py)
ament_add_pytest_test(test_evidence_pack test/test_evidence_pack.py)
```

Run:

```bash
python3 scripts/validate_public_release.py --version v0.1.0 --strict
colcon test --return-code-on-test-failure
colcon test-result --all --verbose
```

Expected: zero validation errors and zero test failures.

- [ ] **Step 5: Build bundles twice and compare checksums**

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
python3 scripts/build_release_bundle.py --version v0.1.0 \
  --output artifacts/release/v0.1.0
cp artifacts/release/v0.1.0/SHA256SUMS /tmp/SHA256SUMS.first
python3 scripts/build_release_bundle.py --version v0.1.0 \
  --output artifacts/release/v0.1.0
cmp /tmp/SHA256SUMS.first artifacts/release/v0.1.0/SHA256SUMS
sha256sum --check artifacts/release/v0.1.0/SHA256SUMS
```

Expected: byte-identical checksum manifest and all assets OK.

- [ ] **Step 6: Commit release tooling**

```bash
git add scripts/build_release_bundle.py scripts/validate_public_release.py \
  scripts/publish_github_release.py src/siminspect_benchmark/CMakeLists.txt \
  src/siminspect_benchmark/test/test_release_bundle.py
git commit -m "build: add deterministic release evidence gate"
```

### Task 6: Rerun exact-commit gates, tag, publish, and verify GitHub Release

**Files:**
- Verify: `docs/validation/evidence-index.json`
- Generate externally: `artifacts/release/v0.1.0/release-evidence-index.json`
- Publish: GitHub tag and Release `v0.1.0`

**Interfaces:**
- Consumes: the clean release-candidate commit and Gate A-D commands from Plans 01-03.
- Produces: annotated tag `v0.1.0`, green tag CI, immutable release assets, and an external index binding exact SHA, URLs, sizes, and checksums.

- [ ] **Step 1: Freeze and rerun Gates A-D on the exact candidate**

```bash
RELEASE_SHA="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
./scripts/verify_foundation.sh
python3 -m siminspect_bringup.acceptance --artifact-root artifacts/runs \
  --require-scenario F00 --require-scenario F06 --require-scenario F07 \
  --require-accepted --commit "$RELEASE_SHA"
ros2 run siminspect_benchmark validate_release_data \
  --matrix src/siminspect_benchmark/config/release_matrix.yaml \
  --raw-root experiments/raw --commit "$RELEASE_SHA" --strict
python3 scripts/validate_public_release.py --version v0.1.0 --strict
```

Expected: Gates A-D pass, E4 reports 60 records/30 pairs, E5 reports 100 records/50 pairs, and public validation reports zero errors. Any code, configuration, claim, or result correction creates a new candidate and restarts this step.

- [ ] **Step 2: Rebuild release assets from the frozen commit**

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$RELEASE_SHA")"
python3 scripts/build_release_bundle.py --version v0.1.0 \
  --output artifacts/release/v0.1.0 --commit "$RELEASE_SHA"
sha256sum --check artifacts/release/v0.1.0/SHA256SUMS
```

Expected: all checksums pass; include `media/demo.mp4`, evidence bundle, raw-trial bundle, and `SHA256SUMS` as release assets.

- [ ] **Step 3: Push the commit, require green CI, and create annotated tag**

```bash
git push origin main
gh run list --commit "$RELEASE_SHA" --workflow ci.yml --limit 1
gh run watch "$(gh run list --commit "$RELEASE_SHA" --workflow ci.yml \
  --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
git tag -a v0.1.0 "$RELEASE_SHA" -m "SimInspect-X v0.1.0"
git push origin v0.1.0
```

Expected: CI exits 0 and `git rev-list -n 1 v0.1.0` equals `$RELEASE_SHA`.

- [ ] **Step 4: Create the GitHub Release and external index**

```bash
gh release create v0.1.0 \
  artifacts/release/v0.1.0/release-evidence.tar.gz \
  artifacts/release/v0.1.0/release-raw-trials.tar.gz \
  artifacts/release/v0.1.0/demo.mp4 \
  artifacts/release/v0.1.0/SHA256SUMS \
  --title "SimInspect-X v0.1.0" \
  --notes-file docs/validation/RESULTS.md --verify-tag
python3 scripts/publish_github_release.py --tag v0.1.0 \
  --commit "$RELEASE_SHA" --repository PoorJeff/SimInspect-X \
  --checksums artifacts/release/v0.1.0/SHA256SUMS \
  --output artifacts/release/v0.1.0/release-evidence-index.json
gh release upload v0.1.0 \
  artifacts/release/v0.1.0/release-evidence-index.json --clobber
```

Expected: the external index uses GitHub download URLs and excludes its own checksum entry, avoiding self-reference.

- [ ] **Step 5: Verify every public locator and declare Gate E**

```bash
gh release verify v0.1.0
gh release view v0.1.0 --json tagName,targetCommitish,assets,url
python3 scripts/publish_github_release.py --tag v0.1.0 \
  --commit "$RELEASE_SHA" --repository PoorJeff/SimInspect-X \
  --verify-remote artifacts/release/v0.1.0/release-evidence-index.json
test "$(git rev-list -n 1 v0.1.0)" = "$RELEASE_SHA"
```

Expected: tag SHA matches, tag CI is green, every asset URL returns the indexed size/checksum, README preview resolves, and Gate E reports PASS. Only now replace the interim status with `validated release v0.1.0`; that wording change requires a subsequent patch release unless it was already represented conditionally by the release badge.

## Plan Acceptance

This plan is complete only when `v0.1.0` points to the exact Gate A-D commit, both READMEs agree, every public number resolves through `claims.json` to preserved raw trials, all curated media resolves to one accepted live F07 run, diagrams regenerate byte-for-byte, deterministic bundles include failures, and the external release index verifies every large asset without self-reference.
