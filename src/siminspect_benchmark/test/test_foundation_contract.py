from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]


def _active_lines(text):
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _has_active_ci_verifier(text):
    pattern = re.compile(
        r"\s*bash\s+-lc\s+['\"]\./scripts/verify_foundation\.sh['\"]\s*(?:#.*)?$"
    )
    return any(pattern.fullmatch(line) for line in _active_lines(text))


def _active_shell_command_index(text, command):
    pattern = re.compile(rf"\s*{re.escape(command)}\s*(?:#.*)?$")
    return next(
        (index for index, line in enumerate(_active_lines(text)) if pattern.fullmatch(line)),
        None,
    )


def _active_shell_prefix_index(text, command):
    pattern = re.compile(rf"\s*{re.escape(command)}(?:\s+|$)")
    return next(
        (index for index, line in enumerate(_active_lines(text)) if pattern.match(line)),
        None,
    )


def _has_active_docker_package(text, package):
    pattern = re.compile(rf"\s*{re.escape(package)}\s*(?:\\\s*)?(?:#.*)?$")
    return any(pattern.fullmatch(line) for line in _active_lines(text))


def _has_active_docker_instruction(text, instruction):
    pattern = re.compile(rf"\s*{re.escape(instruction)}\s*(?:#.*)?$")
    return any(pattern.fullmatch(line) for line in _active_lines(text))


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
    text = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert _has_active_docker_package(text, "sudo")
    assert _has_active_docker_package(text, "build-essential")
    assert _has_active_docker_instruction(text, "RUN rosdep init")
    assert _has_active_docker_instruction(text, "USER siminspect")


def test_ci_delegates_to_shared_verifier():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert _has_active_ci_verifier(workflow)
    assert _active_shell_prefix_index(
        workflow, "colcon test --return-code-on-test-failure"
    ) is None


def test_setup_refreshes_apt_lists_before_rosdep_install():
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    apt_update_index = _active_shell_command_index(setup, "sudo -n apt-get update")
    rosdep_install_index = _active_shell_prefix_index(setup, "rosdep install")
    assert apt_update_index is not None
    assert rosdep_install_index is not None
    assert apt_update_index < rosdep_install_index


def test_ros_interface_files_do_not_start_with_utf8_bom():
    interface_files = sorted(
        path
        for extension in ("msg", "srv", "action")
        for path in ROOT.glob(f"src/**/*.{extension}")
    )
    assert interface_files
    for interface_file in interface_files:
        assert not interface_file.read_bytes().startswith(b"\xef\xbb\xbf"), interface_file


def test_active_instruction_matchers_reject_review_mutations():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    broken_workflow = workflow.replace(
        "bash -lc './scripts/verify_foundation.sh'",
        "echo no-op  # ./scripts/verify_foundation.sh",
    )
    assert broken_workflow != workflow
    assert not _has_active_ci_verifier(broken_workflow)

    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    broken_setup = setup.replace("sudo -n apt-get update", "# sudo -n apt-get update")
    assert broken_setup != setup
    assert _active_shell_command_index(
        broken_setup, "sudo -n apt-get update"
    ) is None

    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    broken_dockerfile = dockerfile.replace("build-essential", "# build-essential", 1)
    assert broken_dockerfile != dockerfile
    assert not _has_active_docker_package(broken_dockerfile, "build-essential")
