from __future__ import annotations

import platform
import socket
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def start_windows_receiver(source: str, project_root: Path) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"ok": False, "error": "Receiver restart is only available on Windows."}

    parsed = urlparse(source)
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in LOCAL_HOSTS:
        return {"ok": False, "error": "Receiver restart is only available for local HTTP ADS-B sources."}

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if _is_port_open(parsed.hostname or "127.0.0.1", port):
        return {"ok": True, "already_running": True, "port": port}

    script = project_root / "scripts" / "start-windows-receiver.ps1"
    if not script.exists():
        return {"ok": False, "error": f"Missing receiver start script: {script}"}

    out_log = project_root / "windows-receiver.out.log"
    err_log = project_root / "windows-receiver.err.log"
    _append_log(out_log, f"SkyLedger receiver start requested for port {port}")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-HttpPort",
        str(port),
    ]

    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    try:
        with out_log.open("a", encoding="utf-8") as stdout, err_log.open("a", encoding="utf-8") as stderr:
            process = subprocess.Popen(  # noqa: S603 - command is a bundled local script.
                command,
                cwd=project_root,
                stdout=stdout,
                stderr=stderr,
                stdin=subprocess.DEVNULL,
                creationflags=flags,
            )
    except OSError as exc:
        _append_log(err_log, f"SkyLedger receiver start failed: {exc}")
        return {"ok": False, "error": str(exc)}

    time.sleep(1)
    exit_code = process.poll()
    if exit_code is not None:
        message = f"Receiver process exited immediately with code {exit_code}."
        _append_log(err_log, message)
        return {"ok": False, "error": message, "port": port}

    return {
        "ok": True,
        "already_running": False,
        "pid": process.pid,
        "port": port,
        "logs": {
            "stdout": str(out_log),
            "stderr": str(err_log),
        },
    }


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _append_log(path: Path, message: str) -> None:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{timestamp}] {message}\n")
