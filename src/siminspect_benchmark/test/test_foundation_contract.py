from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]


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
    assert re.search(r"\bsudo\b", text)
    assert "build-essential" in text
    assert "rosdep init" in text
    assert "USER siminspect" in text


def test_ci_delegates_to_shared_verifier():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "./scripts/verify_foundation.sh" in workflow
    assert "colcon test --return-code-on-test-failure" not in workflow


def test_setup_refreshes_apt_lists_before_rosdep_install():
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "sudo -n apt-get update" in setup
    assert setup.index("sudo -n apt-get update") < setup.index("rosdep install")
