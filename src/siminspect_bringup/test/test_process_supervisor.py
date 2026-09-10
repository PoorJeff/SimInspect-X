import os
import signal
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "siminspect_bringup"))

from siminspect_bringup.component_graph import ProcessSpec  # noqa: E402
from siminspect_bringup.process_supervisor import ProcessSupervisor  # noqa: E402


def _spec(name, script, log_path):
    return ProcessSpec(name, (sys.executable, "-c", script), Path(log_path), ())


def test_start_writes_logs_and_normal_exit_is_reaped(tmp_path):
    supervisor = ProcessSupervisor()
    process = supervisor.start(_spec("normal", "print('hello from child', flush=True)", tmp_path / "normal.log"))
    assert process.wait(timeout=3) == 0
    supervisor.terminate_all(grace_s=0.1)
    supervisor.assert_all_stopped()
    assert "hello from child" in (tmp_path / "normal.log").read_text(encoding="utf-8")


def test_terminate_all_stops_a_long_running_process_and_preserves_log(tmp_path):
    supervisor = ProcessSupervisor()
    process = supervisor.start(_spec("long", "import time; print('started', flush=True); time.sleep(30)", tmp_path / "long.log"))
    time.sleep(0.1)
    supervisor.terminate_all(grace_s=0.2)
    assert process.poll() is not None
    supervisor.assert_all_stopped()
    assert "started" in (tmp_path / "long.log").read_text(encoding="utf-8")


def test_duplicate_name_is_rejected_and_early_death_is_safe(tmp_path):
    supervisor = ProcessSupervisor()
    supervisor.start(_spec("once", "raise SystemExit(3)", tmp_path / "once.log"))
    with pytest.raises(ValueError, match="already started"):
        supervisor.start(_spec("once", "print('duplicate')", tmp_path / "duplicate.log"))
    time.sleep(0.1)
    supervisor.terminate_all(grace_s=0.1)
    supervisor.assert_all_stopped()


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group cleanup requires Ubuntu")
def test_cleanup_reaps_group_when_parent_has_already_exited(tmp_path):
    # The parent waits for the child's signal handlers, then exits while its
    # child stays in the owned group and deliberately ignores graceful stops.
    child_script = (
        "import signal,time; "
        "signal.signal(signal.SIGINT, signal.SIG_IGN); "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "print('ready', flush=True); time.sleep(30)"
    )
    parent_script = (
        "import subprocess,sys; "
        f"child=subprocess.Popen([sys.executable, '-c', {child_script!r}], stdout=subprocess.PIPE); "
        "child.stdout.readline(); print(child.pid, flush=True)"
    )
    supervisor = ProcessSupervisor()
    process = supervisor.start(_spec("orphan", parent_script, tmp_path / "orphan.log"))
    try:
        assert process.wait(timeout=5) == 0
        os.killpg(process.pid, 0)
        with pytest.raises(AssertionError, match="owned processes still running"):
            supervisor.assert_all_stopped()

        supervisor.terminate_all(grace_s=0.3)

        supervisor.assert_all_stopped()
        with pytest.raises(ProcessLookupError):
            os.killpg(process.pid, 0)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
