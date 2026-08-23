from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


MEDIA_TOOL_STATUS_AVAILABLE = "available"
MEDIA_TOOL_STATUS_UNAVAILABLE = "unavailable"
MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE = "executable_but_unusable"
MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR = "version_or_probe_error"


@dataclass(frozen=True)
class MediaToolDiscoveryResult:
    tool_id: str
    command: str
    status: str
    resolved_executable_path: str | None = None
    version: str | None = None
    version_first_line: str | None = None
    reason_code: str | None = None
    message: str | None = None

    @property
    def available(self) -> bool:
        return self.status == MEDIA_TOOL_STATUS_AVAILABLE


RunCallable = Callable[..., subprocess.CompletedProcess[str]]
WhichCallable = Callable[[str], str | None]


def discover_media_tool(
    command: str,
    *,
    tool_id: str | None = None,
    timeout_s: float = 5.0,
    runner: RunCallable = subprocess.run,
    which: WhichCallable | None = None,
) -> MediaToolDiscoveryResult:
    """Resolve and sanity-check a media CLI without accepting caller paths.

    The command comes from trusted code/config. Discovery uses the process PATH
    plus persisted Windows PATH values when available so a newly installed
    winget package can be observed before the parent shell is restarted.
    """

    tool = tool_id or command
    resolver = which or _which_with_effective_path
    resolved = resolver(command)
    if not resolved:
        return MediaToolDiscoveryResult(
            tool_id=tool,
            command=command,
            status=MEDIA_TOOL_STATUS_UNAVAILABLE,
            reason_code=f"{tool.upper()}_NOT_AVAILABLE",
            message=f"{command} executable is not available in PATH.",
        )
    path = Path(resolved)
    if not path.exists() or not path.is_file():
        return MediaToolDiscoveryResult(
            tool_id=tool,
            command=command,
            status=MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
            resolved_executable_path=str(path),
            reason_code=f"{tool.upper()}_EXECUTABLE_INVALID",
            message=f"{command} resolved to a non-file executable path.",
        )
    try:
        completed = runner(
            [str(path), "-version"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return MediaToolDiscoveryResult(
            tool_id=tool,
            command=command,
            status=MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
            resolved_executable_path=str(path),
            reason_code=f"{tool.upper()}_VERSION_TIMEOUT",
            message=f"{command} -version timed out.",
        )
    except Exception as exc:
        return MediaToolDiscoveryResult(
            tool_id=tool,
            command=command,
            status=MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
            resolved_executable_path=str(path),
            reason_code=f"{tool.upper()}_EXECUTABLE_ERROR",
            message=str(exc) or exc.__class__.__name__,
        )
    first_line = _first_nonempty_line(completed.stdout, completed.stderr)
    parsed_version = _parse_version(first_line, expected_tool=tool)
    if completed.returncode != 0 or not parsed_version:
        return MediaToolDiscoveryResult(
            tool_id=tool,
            command=command,
            status=MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR,
            resolved_executable_path=str(path),
            version_first_line=first_line,
            reason_code=f"{tool.upper()}_VERSION_OR_PROBE_ERROR",
            message=(completed.stderr or completed.stdout or f"{command} -version did not return a usable version.").strip()[:500],
        )
    return MediaToolDiscoveryResult(
        tool_id=tool,
        command=command,
        status=MEDIA_TOOL_STATUS_AVAILABLE,
        resolved_executable_path=str(path),
        version=parsed_version,
        version_first_line=first_line,
    )


def media_environment_snapshot() -> dict[str, dict[str, str | bool | None]]:
    return {
        tool_id: _snapshot(discover_media_tool(command, tool_id=tool_id))
        for tool_id, command in {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}.items()
    }


def _snapshot(result: MediaToolDiscoveryResult) -> dict[str, str | bool | None]:
    return {
        "tool_id": result.tool_id,
        "command": result.command,
        "status": result.status,
        "available": result.available,
        "resolved_executable_path": result.resolved_executable_path,
        "version": result.version,
        "version_first_line": result.version_first_line,
        "reason_code": result.reason_code,
        "message": result.message,
    }


def _effective_path() -> str | None:
    values = [os.environ.get("PATH") or os.environ.get("Path") or ""]
    values.extend(_windows_persisted_path_values())
    combined = os.pathsep.join(value for value in values if value)
    return combined or None


def _which_with_effective_path(command: str) -> str | None:
    try:
        return shutil.which(command, path=_effective_path())
    except TypeError:
        return shutil.which(command)


def _windows_persisted_path_values() -> list[str]:
    if os.name != "nt":
        return []
    try:
        import winreg
    except Exception:  # pragma: no cover - non-Windows or restricted Python
        return []
    rows: list[str] = []
    locations: Sequence[tuple[object, str]] = (
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    )
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                value, _kind = winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        if isinstance(value, str) and value:
            rows.append(os.path.expandvars(value))
    return rows


def _first_nonempty_line(*streams: str | None) -> str | None:
    for stream in streams:
        for line in str(stream or "").splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
    return None


def _parse_version(line: str | None, *, expected_tool: str) -> str | None:
    if not line:
        return None
    match = re.match(rf"^{re.escape(expected_tool)}\s+version\s+(\S+)", line, flags=re.IGNORECASE)
    return match.group(1) if match else None
