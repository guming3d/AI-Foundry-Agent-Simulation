import sys
import time
from pathlib import Path

import pytest

from src.core import config
from src.core.daemon_service import DaemonService, _write_json_atomic
import subprocess


def _proc_state(pid: int) -> str | None:
    stat = Path(f"/proc/{pid}/stat")
    try:
        data = stat.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception:
        return None
    end = data.rfind(")")
    if end == -1:
        return None
    idx = end + 2
    if idx >= len(data):
        return None
    return data[idx]


@pytest.mark.unit
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="zombie detection requires /proc")
def test_is_running_handles_zombie_pid(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "DAEMON_RESULTS_DIR", tmp_path)
    service = DaemonService()

    proc = subprocess.Popen([sys.executable, "-c", "import os; os._exit(0)"])
    pid = proc.pid
    service._write_pid(pid)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        if _proc_state(pid) == "Z":
            break
        time.sleep(0.01)

    assert _proc_state(pid) == "Z"
    assert service.is_running() is False
    assert not service.pid_path.exists()

    deadline = time.time() + 2.0
    while time.time() < deadline and Path(f"/proc/{pid}").exists():
        time.sleep(0.01)
    assert not Path(f"/proc/{pid}").exists()


@pytest.mark.unit
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="process lifecycle assertions require /proc")
def test_stop_reaps_process_and_updates_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "DAEMON_RESULTS_DIR", tmp_path)
    service = DaemonService()

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    pid = proc.pid
    service._write_pid(pid)
    _write_json_atomic(service.state_path, {"pid": pid, "started_at": "test"})

    try:
        ok, message = service.stop(timeout=2.0)
        assert ok, message
        assert not service.pid_path.exists()

        deadline = time.time() + 2.0
        while time.time() < deadline and Path(f"/proc/{pid}").exists():
            time.sleep(0.01)
        assert not Path(f"/proc/{pid}").exists()

        state = service.read_state()
        assert state.get("pid") == 0
        assert "stopped_at" in state
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=0.2)
        except Exception:
            pass

