#!/usr/bin/env python3
"""Create and inspect the isolated runtime used by the BOSS Zhipin skill."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv


UPSTREAM_COMMIT = "9d38ed1a3a5f6c5c2f37b865b0748454234e7c70"
PACKAGE_SPEC = (
    "kabi-boss-cli @ "
    f"https://github.com/jackwener/boss-cli/archive/{UPSTREAM_COMMIT}.zip"
)
MIN_PYTHON = (3, 10)
RUNTIME_ENV = "BOSS_ZHIPIN_SKILL_RUNTIME"


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def runtime_root() -> Path:
    override = os.environ.get(RUNTIME_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "boss-zhipin-codex-skill"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "boss-zhipin-codex-skill"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "boss-zhipin-codex-skill"


def venv_root() -> Path:
    return runtime_root() / "venv"


def runtime_python() -> Path:
    if os.name == "nt":
        return venv_root() / "Scripts" / "python.exe"
    return venv_root() / "bin" / "python"


def boss_executable() -> Path:
    if os.name == "nt":
        return venv_root() / "Scripts" / "boss.exe"
    return venv_root() / "bin" / "boss"


def supported_python() -> bool:
    return sys.version_info >= MIN_PYTHON


def command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else None


def recruiter_available(executable: Path | None = None) -> bool:
    target = executable or boss_executable()
    if not target.is_file():
        return False
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    environment.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        result = subprocess.run(
            [str(target), "recruiter", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    combined = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and "Commands:" in combined and "resume" in combined


def status_payload() -> dict[str, object]:
    executable = boss_executable()
    return {
        "ok": supported_python(),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "minimum_python": ".".join(map(str, MIN_PYTHON)),
        "runtime_root": str(runtime_root()),
        "package": PACKAGE_SPEC,
        "installed": executable.is_file(),
        "recruiter_available": recruiter_available(executable),
        "boss_executable": str(executable),
        "boss_version": command_output([str(executable), "--version"]) if executable.is_file() else None,
    }


def install_runtime(upgrade: bool = False) -> dict[str, object]:
    if not supported_python():
        raise RuntimeError(
            f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 或更高版本，"
            f"当前为 {platform.python_version()}。"
        )

    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    python_path = runtime_python()
    if not python_path.is_file():
        venv.EnvBuilder(with_pip=True, clear=False).create(venv_root())

    command = [
        str(python_path),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
    ]
    if upgrade:
        command.append("--upgrade")
    command.append(PACKAGE_SPEC)
    subprocess.run(command, check=True)

    payload = status_payload()
    if not payload["installed"]:
        raise RuntimeError("依赖安装完成，但没有找到 boss 可执行文件。")
    if not payload["recruiter_available"]:
        raise RuntimeError("依赖已安装，但招聘端命令不可用；拒绝继续使用不完整运行时。")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理 BOSS 直聘 Skill 的隔离运行时")
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("check", help="只检查环境和安装状态")
    install = subparsers.add_parser("install", help="创建隔离环境并安装固定版本依赖")
    install.add_argument("--upgrade", action="store_true", help="重新安装固定版本依赖")
    subparsers.add_parser("path", help="输出 boss 可执行文件路径")
    return parser


def main() -> int:
    configure_utf8_console()
    args = build_parser().parse_args()
    try:
        if args.action == "check":
            payload = status_payload()
        elif args.action == "install":
            payload = install_runtime(upgrade=args.upgrade)
        else:
            print(boss_executable())
            return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
