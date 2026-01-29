"""
Daemon service utilities for running the simulation daemon out-of-process.

Provides process management, status checks, and metrics retrieval so the
daemon can persist beyond the UI lifecycle.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core import config
from src.core.daemon_runner import DaemonRunner, DaemonConfig
from src.models.agent import CreatedAgent
from src.templates.template_loader import TemplateLoader


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    tmp_path.replace(path)


def _linux_process_state(pid: int) -> Optional[str]:
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        data = stat_path.read_text(encoding="utf-8")
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


def _pid_is_zombie(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("linux"):
        state = _linux_process_state(pid)
        return state in {"Z", "X"}
    return False


def _try_reap_pid(pid: int) -> bool:
    if pid <= 0 or not hasattr(os, "waitpid"):
        return False
    try:
        waited_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return False
    except OSError:
        return False
    return waited_pid == pid


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if _pid_is_zombie(pid):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class DaemonService:
    """Manage the long-running daemon as a background process."""

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        # Resolve daemon artifacts relative to the repo root so the UI can be launched
        # from any working directory and still attach to the same background daemon.
        self.daemon_dir = self.repo_root / config.DAEMON_RESULTS_DIR
        self.daemon_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.daemon_dir / "daemon_state.json"
        self.metrics_path = self.daemon_dir / "daemon_metrics.json"
        self.history_path = self.daemon_dir / "daemon_history.jsonl"
        self.pid_path = self.daemon_dir / "daemon.pid"
        self.log_path = self.daemon_dir / "daemon.log"

    def _read_pid(self) -> Optional[int]:
        if not self.pid_path.exists():
            return None
        try:
            return int(self.pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def _write_pid(self, pid: int) -> None:
        self.pid_path.write_text(str(pid), encoding="utf-8")

    def _clear_pid(self) -> None:
        if self.pid_path.exists():
            self.pid_path.unlink()

    def _mark_stopped(self) -> None:
        state = self.read_state()
        if not state:
            return
        state["pid"] = 0
        state["stopped_at"] = datetime.now().isoformat()
        _write_json_atomic(self.state_path, state)

    def is_running(self) -> bool:
        pid = self._read_pid()
        if pid:
            if _pid_is_running(pid):
                return True
            if _pid_is_zombie(pid):
                _try_reap_pid(pid)
            self._clear_pid()

        metrics = self.read_metrics()
        metrics_pid = int(metrics.get("pid", 0) or 0) if metrics else 0
        if metrics_pid:
            if _pid_is_running(metrics_pid):
                self._write_pid(metrics_pid)
                return True
            if _pid_is_zombie(metrics_pid):
                _try_reap_pid(metrics_pid)

        state = self.read_state()
        state_pid = int(state.get("pid", 0) or 0) if state else 0
        if state_pid:
            if _pid_is_running(state_pid):
                self._write_pid(state_pid)
                return True
            if _pid_is_zombie(state_pid):
                _try_reap_pid(state_pid)
        return False

    def read_metrics(self) -> Dict[str, Any]:
        return _read_json(self.metrics_path)

    def read_history(self, limit: int = 120) -> List[Dict[str, Any]]:
        """Read the last N history samples from the append-only JSONL history file."""
        path = self.history_path
        if not path.exists():
            return []

        # Tail the file without reading it all (can be huge for long-running runs).
        try:
            with path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                end = handle.tell()
                block = 8192
                data = b""
                lines: List[bytes] = []
                while end > 0 and len(lines) <= limit:
                    read_size = block if end >= block else end
                    end -= read_size
                    handle.seek(end)
                    data = handle.read(read_size) + data
                    lines = data.splitlines()
                    if end == 0:
                        break
                tail = lines[-limit:]
        except Exception:
            return []

        out: List[Dict[str, Any]] = []
        for raw in tail:
            try:
                out.append(json.loads(raw.decode("utf-8")))
            except Exception:
                continue
        return out

    def read_state(self) -> Dict[str, Any]:
        return _read_json(self.state_path)

    def _serialize_agents(self, agents: List[CreatedAgent]) -> List[Dict[str, Any]]:
        serialized = []
        for agent in agents:
            serialized.append(
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "azure_id": agent.azure_id,
                    "version": agent.version,
                    "model": agent.model,
                    "org_id": agent.org_id,
                    "agent_type": agent.agent_type,
                }
            )
        return serialized

    def start(
        self,
        daemon_config: DaemonConfig,
        agents: List[CreatedAgent],
        profile_id: str,
        profile_name: str,
    ) -> Tuple[bool, str]:
        if self.is_running():
            return False, "Daemon already running"
        if not agents:
            return False, "No agents selected"

        daemon_config.output_dir = str(self.daemon_dir)
        state = {
            "started_at": datetime.now().isoformat(),
            "profile_id": profile_id,
            "profile_name": profile_name,
            "config": asdict(daemon_config),
            "agents": self._serialize_agents(agents),
        }
        _write_json_atomic(self.state_path, state)

        cmd = [
            sys.executable,
            "-m",
            "src.core.daemon_service",
            "run",
            "--state",
            str(self.state_path),
        ]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_path.open("a", encoding="utf-8")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self.repo_root,
                stdout=log_handle,
                stderr=log_handle,
                start_new_session=True,
            )
        except Exception as exc:
            log_handle.close()
            return False, f"Failed to start daemon: {exc}"

        log_handle.close()
        self._write_pid(proc.pid)
        state["pid"] = proc.pid
        _write_json_atomic(self.state_path, state)
        return True, "Daemon started"

    def stop(self, timeout: float = 5.0) -> Tuple[bool, str]:
        pid = self._read_pid()
        if not pid:
            metrics = self.read_metrics()
            metrics_pid = int(metrics.get("pid", 0) or 0) if metrics else 0
            state = self.read_state()
            state_pid = int(state.get("pid", 0) or 0) if state else 0
            if metrics_pid and _pid_is_running(metrics_pid):
                pid = metrics_pid
            elif state_pid and _pid_is_running(state_pid):
                pid = state_pid
            elif metrics_pid and _pid_is_zombie(metrics_pid):
                pid = metrics_pid
            elif state_pid and _pid_is_zombie(state_pid):
                pid = state_pid
            else:
                pid = metrics_pid or state_pid
            if pid:
                self._write_pid(pid)
            else:
                return False, "Daemon is not running"
        if not _pid_is_running(pid):
            if _pid_is_zombie(pid):
                _try_reap_pid(pid)
            self._clear_pid()
            self._mark_stopped()
            return True, "Daemon stopped"

        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as exc:
            return False, f"Failed to stop daemon: {exc}"

        start = time.time()
        while time.time() - start < timeout:
            if not _pid_is_running(pid):
                _try_reap_pid(pid)
                self._clear_pid()
                self._mark_stopped()
                return True, "Daemon stopped"
            time.sleep(0.2)

        try:
            os.kill(pid, signal.SIGKILL)
        except Exception as exc:
            return False, f"Timed out stopping daemon: {exc}"

        time.sleep(0.2)
        if not _pid_is_running(pid):
            _try_reap_pid(pid)
            self._clear_pid()
            self._mark_stopped()
            return True, "Daemon force-stopped"

        return False, "Timed out stopping daemon"


def _load_agents(agent_rows: List[Dict[str, Any]]) -> List[CreatedAgent]:
    agents: List[CreatedAgent] = []
    for row in agent_rows:
        try:
            agents.append(CreatedAgent(**row))
        except Exception:
            continue
    return agents


def run_daemon(state_path: Path) -> int:
    """Run the daemon loop in the foreground for background process execution."""
    service = DaemonService()
    state = _read_json(state_path)
    if not state:
        return 1

    existing_pid = service._read_pid()
    current_pid = os.getpid()
    if existing_pid and existing_pid != current_pid and _pid_is_running(existing_pid):
        return 2
    service._write_pid(current_pid)

    profile_id = state.get("profile_id")
    if not profile_id:
        return 3

    try:
        profile = TemplateLoader().load_template(profile_id)
    except Exception:
        return 4

    config_data = state.get("config", {})
    # Allow old/new daemon state JSON to be read across versions.
    from dataclasses import fields
    allowed = {f.name for f in fields(DaemonConfig)}
    filtered = {k: v for k, v in (config_data or {}).items() if k in allowed}
    daemon_config = DaemonConfig(**filtered)
    daemon_config.output_dir = str(service.daemon_dir)

    agents = _load_agents(state.get("agents", []))
    runner = DaemonRunner(agents=agents, profile=profile)

    log_handle = service.log_path.open("a", encoding="utf-8")

    def log_callback(message: str) -> None:
        log_handle.write(message + "\n")
        log_handle.flush()

    def metrics_callback(_: Dict[str, Any]) -> None:
        return

    def handle_signal(_signum, _frame) -> None:
        runner.request_stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        runner.run_blocking(daemon_config, log_callback=log_callback, metrics_callback=metrics_callback)
    finally:
        log_handle.close()
        service._clear_pid()
        state = _read_json(state_path)
        if state:
            state["pid"] = 0
            state["stopped_at"] = datetime.now().isoformat()
            _write_json_atomic(state_path, state)

    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Simulation daemon service helper")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run daemon process")
    run_parser.add_argument("--state", default=str(DaemonService().state_path))

    args = parser.parse_args()

    if args.command == "run":
        return run_daemon(Path(args.state))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
