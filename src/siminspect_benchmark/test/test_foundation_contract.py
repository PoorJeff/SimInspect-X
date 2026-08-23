from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[3]


def _active_lines(text):
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _indent(line):
    return len(line) - len(line.lstrip())


def _workflow_run_at(lines, index):
    line = lines[index]
    if line.lstrip().startswith("#"):
        return None, index + 1
    match = re.match(r"^\s*(?:-\s+)?run:\s*(?P<value>.*)$", line)
    if not match:
        return None, index + 1

    value = match.group("value")
    if not value.startswith("|"):
        return value, index + 1

    run_indent = line.index("run:")
    body = []
    index += 1
    while index < len(lines):
        next_line = lines[index]
        if next_line.strip() and _indent(next_line) <= run_indent:
            break
        body.append(next_line)
        index += 1
    return "\n".join(body), index


def _workflow_run_commands(workflow):
    lines = workflow.splitlines()
    commands = []
    index = 0
    while index < len(lines):
        command, next_index = _workflow_run_at(lines, index)
        if command is not None:
            commands.append(command)
        index = next_index
    return commands


def _workflow_step_run(workflow, name):
    lines = workflow.splitlines()
    step_pattern = re.compile(
        rf"^(?P<indent>\s*)-\s+name:\s+{re.escape(name)}\s*(?:#.*)?$"
    )
    for index, line in enumerate(lines):
        step_match = step_pattern.fullmatch(line)
        if not step_match:
            continue
        step_indent = len(step_match.group("indent"))
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            if (
                candidate.strip()
                and _indent(candidate) <= step_indent
                and candidate.lstrip().startswith("- ")
            ):
                break
            command, next_cursor = _workflow_run_at(lines, cursor)
            if command is not None and _indent(candidate) > step_indent:
                return command
            cursor = next_cursor
    return None


def _strip_shell_comment(line):
    quote = None
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
        elif character == "\\" and quote != "'":
            escaped = True
        elif character in "'\"":
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
        elif character == "#" and quote is None and (
            index == 0 or line[index - 1].isspace()
        ):
            return line[:index]
    return line


def _shell_executed_lines(script):
    lines = []
    heredoc_delimiters = []
    heredoc_pattern = re.compile(
        r"""<<-?\s*(?:'([^']+)'|"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))"""
    )
    for raw_line in script.splitlines():
        if heredoc_delimiters:
            if raw_line.strip() == heredoc_delimiters[0]:
                heredoc_delimiters.pop(0)
            continue
        line = _strip_shell_comment(raw_line).strip()
        if not line:
            continue
        for match in heredoc_pattern.finditer(line):
            heredoc_delimiters.append(next(group for group in match.groups() if group))
        lines.append(line)
    return lines


def _join_shell_continuations(lines):
    command = []
    for line in lines:
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            command.append(stripped[:-1].rstrip())
        else:
            command.append(stripped)
    return " ".join(command)


def _has_active_ci_verifier(workflow):
    run = _workflow_step_run(workflow, "Build and test (headless)")
    if run is None:
        return False
    try:
        tokens = shlex.split(_join_shell_continuations(_shell_executed_lines(run)))
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


def _docker_run_instructions(text):
    lines = text.splitlines()
    instructions = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.match(r"^\s*RUN\s+(?P<command>.*)$", line)
        if not match:
            index += 1
            continue
        parts = [_strip_shell_comment(match.group("command")).rstrip()]
        while parts[-1].endswith("\\") and index + 1 < len(lines):
            parts[-1] = parts[-1][:-1].rstrip()
            index += 1
            parts.append(_strip_shell_comment(lines[index]).strip())
        instructions.append(" ".join(parts))
        index += 1
    return instructions


def _has_active_docker_package(text, package):
    for instruction in _docker_run_instructions(text):
        try:
            tokens = shlex.split(instruction)
        except ValueError:
            continue
        for index in range(len(tokens) - 1):
            if tokens[index:index + 2] != ["apt-get", "install"]:
                continue
            for token in tokens[index + 2:]:
                if token in {"&&", ";", "||", "|"}:
                    break
                if token == package:
                    return True
    return False


def _has_active_docker_instruction(text, instruction):
    if instruction.startswith("RUN "):
        return instruction.removeprefix("RUN ") in _docker_run_instructions(text)
    pattern = re.compile(rf"\s*{re.escape(instruction)}\s*(?:#.*)?$")
    return any(pattern.fullmatch(line) for line in _active_lines(text))


def _line_invokes_colcon_test(line):
    direct_pattern = re.compile(
        r"(?:^|&&|\|\||[;|])\s*colcon\s+test\s+--return-code-on-test-failure\b"
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
    return any(_line_invokes_colcon_test(line) for line in _shell_executed_lines(script))


def _workflow_has_duplicate_colcon_test(workflow):
    return any(
        _shell_invokes_colcon_test(command)
        for command in _workflow_run_commands(workflow)
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
    assert _has_active_docker_package(text, "sudo")
    assert _has_active_docker_package(text, "build-essential")
    assert _has_active_docker_instruction(text, "RUN rosdep init")
    assert _has_active_docker_instruction(text, "USER siminspect")


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
    assert not _has_active_docker_package(broken_dockerfile, "build-essential")

    echo_dockerfile = dockerfile.replace("build-essential", "removed-build-essential", 1)
    echo_dockerfile += "\n".join(("", "RUN echo \\", "    build-essential", ""))
    assert not _has_active_docker_package(echo_dockerfile, "build-essential")

    duplicate_runs = (
        "run: colcon test --return-code-on-test-failure",
        "run: bash -lc 'colcon test --return-code-on-test-failure'",
        "run: |\n          cd . && colcon test --return-code-on-test-failure",
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
