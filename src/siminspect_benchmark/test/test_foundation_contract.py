from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_MOUNT = "$" + "{{ github.workspace }}:/home/siminspect/ws"
CANONICAL_HEADLESS_RUN = "\n".join(
    [
        "docker run --rm --user root \\",
        "  -e DISPLAY= \\",
        f'  -v "{WORKSPACE_MOUNT}" \\',
        "  -w /home/siminspect/ws \\",
        "  siminspect-x:ci \\",
        "  bash -lc './scripts/verify_foundation.sh'",
    ]
) + "\n"
APT_BLOCK = re.compile(
    r"(?m)^RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
    r"(?P<packages>(?:^[ \t]+[^\n]* \\\n)+?)"
    r"^[ \t]+&& add-apt-repository universe \\\n"
)
INLINE_COLCON_TEST = "colcon test --return-code-on-test-failure"


def _workflow_steps(workflow):
    try:
        return yaml.safe_load(workflow)["jobs"]["build-and-test"]["steps"]
    except (KeyError, TypeError, yaml.YAMLError):
        return []


def _workflow_run_values(workflow):
    try:
        jobs = yaml.safe_load(workflow)["jobs"].values()
    except (AttributeError, KeyError, TypeError, yaml.YAMLError):
        return []
    return [
        step["run"]
        for job in jobs
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    ]


def _has_canonical_ci_verifier(workflow):
    run = next(
        (
            step.get("run")
            for step in _workflow_steps(workflow)
            if isinstance(step, dict) and step.get("name") == "Build and test (headless)"
        ),
        None,
    )
    return run == CANONICAL_HEADLESS_RUN


def _workflow_has_inline_colcon_test(workflow):
    return any(INLINE_COLCON_TEST in run for run in _workflow_run_values(workflow))


def _canonical_apt_block(dockerfile):
    match = APT_BLOCK.search(dockerfile)
    return match.group("packages") if match else ""


def _has_canonical_apt_package(dockerfile, package):
    return bool(
        re.search(
            rf"(?m)^[ \t]*{re.escape(package)}[ \t]+\\[ \t]*$",
            _canonical_apt_block(dockerfile),
        )
    )


def _active_shell_command_index(text, command):
    pattern = re.compile(rf"\s*{re.escape(command)}\s*(?:#.*)?$")
    return next(
        (
            index
            for index, line in enumerate(text.splitlines())
            if not line.lstrip().startswith("#") and pattern.fullmatch(line)
        ),
        None,
    )


def _apt_refresh_precedes_rosdep_install(setup):
    apt_update = _active_shell_command_index(setup, "sudo -n apt-get update")
    rosdep_install = next(
        (
            index
            for index, line in enumerate(setup.splitlines())
            if not line.lstrip().startswith("#")
            and re.match(r"\s*rosdep\s+install(?:\s+|$)", line)
        ),
        None,
    )
    return (
        apt_update is not None
        and rosdep_install is not None
        and apt_update < rosdep_install
    )


def test_all_cmake_install_directories_exist():
    for cmake in ROOT.glob("src/*/CMakeLists.txt"):
        text = cmake.read_text(encoding="utf-8")
        for body in re.findall(r"install\(DIRECTORY\s+([^\)]+?)\s+DESTINATION", text, re.S):
            for name in body.split():
                assert (cmake.parent / name).is_dir(), f"{cmake}: missing {name}"


def test_all_docker_builds_use_root_context():
    demo = (ROOT / "run_demo.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    builds = re.findall(r"docker build[^\n]+", demo)
    assert builds
    for build in builds:
        assert "-f docker/Dockerfile" in build
        assert build.split()[-1] == "."
    assert "context: ." in workflow
    assert "file: docker/Dockerfile" in workflow


def test_dockerfile_initializes_required_runtime_tools():
    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert _has_canonical_apt_package(dockerfile, "sudo")
    assert _has_canonical_apt_package(dockerfile, "build-essential")
    assert re.search(r"(?m)^RUN\s+rosdep\s+init\s*(?:#.*)?$", dockerfile)
    assert re.search(r"(?m)^USER\s+siminspect\s*(?:#.*)?$", dockerfile)


def test_ci_delegates_to_shared_verifier():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert _has_canonical_ci_verifier(workflow)
    assert not _workflow_has_inline_colcon_test(workflow)


def test_setup_refreshes_apt_lists_before_rosdep_install():
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert _apt_refresh_precedes_rosdep_install(setup)


def test_ros_interface_files_do_not_start_with_utf8_bom():
    interface_files = sorted(
        path
        for extension in ("msg", "srv", "action")
        for path in ROOT.glob(f"src/**/*.{extension}")
    )
    assert interface_files
    for interface_file in interface_files:
        assert not interface_file.read_bytes().startswith(b"\xef\xbb\xbf"), interface_file


def test_canonical_contract_rejects_review_mutations():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    no_op_workflow = workflow.replace(
        "bash -lc './scripts/verify_foundation.sh'",
        "echo no-op  # ./scripts/verify_foundation.sh",
    )
    assert not _has_canonical_ci_verifier(no_op_workflow)

    heredoc_workflow = """
jobs:
  build-and-test:
    steps:
      - name: Build and test (headless)
        run: |
          cat <<'EOF'
          bash -lc './scripts/verify_foundation.sh'
          EOF
"""
    assert not _has_canonical_ci_verifier(heredoc_workflow)

    missing_continuations = workflow.replace(" " + "\\\n", "\n")
    assert not _has_canonical_ci_verifier(missing_continuations)

    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert not _apt_refresh_precedes_rosdep_install(
        setup.replace("sudo -n apt-get update", "# sudo -n apt-get update")
    )
    assert not _apt_refresh_precedes_rosdep_install(
        setup.replace(
            "sudo -n apt-get update\nrosdep install",
            "rosdep install\nsudo -n apt-get update",
        )
    )

    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert not _has_canonical_apt_package(
        dockerfile.replace("build-essential", "# build-essential", 1),
        "build-essential",
    )
    echo_dockerfile = dockerfile.replace(
        "build-essential", "removed-build-essential", 1
    )
    echo_dockerfile += "\nRUN echo build-essential\n"
    assert not _has_canonical_apt_package(echo_dockerfile, "build-essential")

    echo_apt_dockerfile = dockerfile.replace(
        "build-essential", "removed-build-essential", 1
    )
    echo_apt_dockerfile += "\nRUN echo apt-get install build-essential\n"
    assert not _has_canonical_apt_package(echo_apt_dockerfile, "build-essential")

    cross_block_echo = dockerfile.replace(
        "build-essential", "removed-build-essential", 1
    ).replace(
        "ENV LANG=en_US.UTF-8",
        "RUN echo \\\n    apt-get install \\\n    build-essential \\\n\nENV LANG=en_US.UTF-8",
    )
    assert not _has_canonical_apt_package(cross_block_echo, "build-essential")

    duplicate_runs = (
        "run: colcon test --return-code-on-test-failure",
        "run: bash -lc 'colcon test --return-code-on-test-failure'",
        "run: |\n          cd . && colcon test --return-code-on-test-failure",
        "run: FOO=1 colcon test --return-code-on-test-failure",
        'run: "colcon test --return-code-on-test-failure"',
        "run: FOO='value with spaces' colcon test --return-code-on-test-failure",
        "run: >-\n          colcon test --return-code-on-test-failure",
    )
    for run in duplicate_runs:
        duplicate_workflow = f"{workflow}\n      - name: Duplicate test\n        {run}\n"
        assert _workflow_has_inline_colcon_test(duplicate_workflow)

    other_job_duplicate = f"{workflow}\n  unrelated:\n    steps:\n      - run: {INLINE_COLCON_TEST}\n"
    assert _workflow_has_inline_colcon_test(other_job_duplicate)

    inert_colcon_workflow = """
jobs:
  build-and-test:
    steps:
      - name: Inert text
        run: |
          cat <<'EOF'
          colcon test --return-code-on-test-failure
          EOF
"""
    assert _workflow_has_inline_colcon_test(inert_colcon_workflow)
