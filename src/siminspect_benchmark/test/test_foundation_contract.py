from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[3]


def _active_lines(text):
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _workflow_runs(workflow):
    lines = workflow.splitlines()
    runs = []
    step_name = None
    index = 0
    while index < len(lines):
        line = lines[index]
        step_match = re.fullmatch(r"\s*-\s+name:\s+(?P<name>.+?)\s*(?:#.*)?", line)
        if step_match:
            step_name = step_match.group("name")
            index += 1
            continue
        if re.match(r"^\s*-\s+", line):
            step_name = None
        match = re.match(r"^\s*(?:-\s+)?run:\s*(?P<value>.*)$", line)
        if not match or line.lstrip().startswith("#"):
            index += 1
            continue
        value = match.group("value")
        if value.startswith("|"):
            run_indent = line.index("run:")
            end = index + 1
            while end < len(lines):
                next_line = lines[end]
                if (
                    next_line.strip()
                    and len(next_line) - len(next_line.lstrip()) <= run_indent
                ):
                    break
                end += 1
            value = "\n".join(lines[index + 1:end])
            index = end
        else:
            index += 1
        runs.append((step_name, value))
    return runs


def _executed_shell_lines(script):
    lines = []
    heredoc_delimiter = None
    for raw_line in script.splitlines():
        if heredoc_delimiter:
            if raw_line.strip() == heredoc_delimiter:
                heredoc_delimiter = None
            continue
        line = raw_line.strip()
        if not line:
            continue
        line = line.split(" #", 1)[0].rstrip()
        if not line or line.startswith("#"):
            continue
        heredoc_match = re.search(
            r"""<<-?\s*['"]?([A-Za-z_][A-Za-z0-9_]*)['"]?""", line
        )
        if heredoc_match:
            heredoc_delimiter = heredoc_match.group(1)
        lines.append(line)
    return lines


def _has_active_ci_verifier(workflow):
    run = next(
        (
            command
            for step_name, command in _workflow_runs(workflow)
            if step_name == "Build and test (headless)"
        ),
        None,
    )
    if run is None:
        return False
    try:
        tokens = shlex.split(
            " ".join(line.rstrip("\\").rstrip() for line in _executed_shell_lines(run))
        )
    except ValueError:
        return False
    return tokens == [
        "docker",
        "run",
        "--rm",
        "--user",
        "root",
        "-e",
        "DISPLAY=",
        "-v",
        "$" + "{{ github.workspace }}:/home/siminspect/ws",
        "-w",
        "/home/siminspect/ws",
        "siminspect-x:ci",
        "bash",
        "-lc",
        "./scripts/verify_foundation.sh",
    ]


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


def _has_docker_apt_package(text, package):
    for command in re.findall(r"(?m)^RUN\s+((?:[^\n]*\\\n)*[^\n]*)", text):
        command = "\n".join(
            line.split(" #", 1)[0]
            for line in command.splitlines()
            if not line.lstrip().startswith("#")
        ).replace("\\\n", " ")
        try:
            apt_install = re.search(r"\bapt-get\s+install\b(?P<packages>.*)", command)
            tokens = shlex.split(apt_install.group("packages")) if apt_install else []
        except ValueError:
            continue
        for token in tokens:
            if token in {"&&", ";", "||", "|"}:
                break
            if token == package:
                return True
    return False


def _line_invokes_colcon_test(line):
    direct_pattern = re.compile(
        r"(?:^|&&|\|\||[;|])\s*(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)*"
        r"colcon\s+test\s+--return-code-on-test-failure\b"
    )
    if direct_pattern.search(line):
        return True
    bash_pattern = re.compile(r"""\bbash\s+-lc\s+('([^']*)'|"([^"]*)")""")
    for match in bash_pattern.finditer(line):
        nested_command = match.group(2) or match.group(3)
        if _shell_invokes_colcon_test(nested_command):
            return True
    return False


def _shell_invokes_colcon_test(script):
    return any(_line_invokes_colcon_test(line) for line in _executed_shell_lines(script))


def _workflow_has_duplicate_colcon_test(workflow):
    return any(
        _shell_invokes_colcon_test(command)
        for _, command in _workflow_runs(workflow)
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
    text = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert _has_docker_apt_package(text, "sudo")
    assert _has_docker_apt_package(text, "build-essential")
    assert re.search(r"(?m)^RUN\s+rosdep\s+init\s*(?:#.*)?$", text)
    assert re.search(r"(?m)^USER\s+siminspect\s*(?:#.*)?$", text)


def test_ci_delegates_to_shared_verifier():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert _has_active_ci_verifier(workflow)
    assert not _workflow_has_duplicate_colcon_test(workflow)


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

    heredoc_workflow = """
      - name: Build and test (headless)
        run: |
          cat <<'EOF'
          bash -lc './scripts/verify_foundation.sh'
          EOF
"""
    assert not _has_active_ci_verifier(heredoc_workflow)

    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    broken_setup = setup.replace("sudo -n apt-get update", "# sudo -n apt-get update")
    assert broken_setup != setup
    assert _active_shell_command_index(
        broken_setup, "sudo -n apt-get update"
    ) is None

    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    broken_dockerfile = dockerfile.replace("build-essential", "# build-essential", 1)
    assert broken_dockerfile != dockerfile
    assert not _has_docker_apt_package(broken_dockerfile, "build-essential")

    echo_dockerfile = dockerfile.replace("build-essential", "removed-build-essential", 1)
    echo_dockerfile += "\n".join(("", "RUN echo \\", "    build-essential", ""))
    assert not _has_docker_apt_package(echo_dockerfile, "build-essential")

    duplicate_runs = (
        "run: colcon test --return-code-on-test-failure",
        "run: bash -lc 'colcon test --return-code-on-test-failure'",
        "run: |\n          cd . && colcon test --return-code-on-test-failure",
        "run: FOO=1 colcon test --return-code-on-test-failure",
    )
    for run in duplicate_runs:
        duplicate_workflow = (
            f"{workflow}\n      - name: Duplicate test\n        {run}\n"
        )
        assert _workflow_has_duplicate_colcon_test(duplicate_workflow)

    inert_workflow = """
      - name: Inert text
        run: |
          cat <<'EOF'
          colcon test --return-code-on-test-failure
          EOF
          echo no-op  # colcon test --return-code-on-test-failure
"""
    assert not _workflow_has_duplicate_colcon_test(inert_workflow)
