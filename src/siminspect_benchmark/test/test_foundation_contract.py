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
    assert "docker build" in demo
    assert "docker/" not in re.search(r"docker build[^\n]+", demo).group(0).split()[-1]
    assert "context: ." in workflow
    assert "file: docker/Dockerfile" in workflow
