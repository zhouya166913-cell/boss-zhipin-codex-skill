#!/usr/bin/env python3
"""Run boss-cli with explicit guards around local and remote mutations."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from bootstrap import boss_executable, runtime_python


TOP_LEVEL_REMOTE_WRITES = {"greet", "batch-greet"}
TOP_LEVEL_LOCAL_WRITES = {"export", "logout"}
TOP_LEVEL_READS = {
    "--help",
    "--version",
    "login",
    "status",
    "me",
    "search",
    "recommend",
    "detail",
    "show",
    "history",
    "cities",
    "applied",
    "interviews",
    "chat",
}
RECRUITER_REMOTE_WRITES = {
    "greet",
    "batch-view",
    "reply",
    "job-close",
    "job-reopen",
    "request-resume",
    "exchange-phone",
    "exchange-wechat",
    "invite-interview",
    "mark-unsuitable",
}
RECRUITER_LOCAL_WRITES = {"export", "resume-download"}
RECRUITER_READS = {
    "--help",
    "jobs",
    "search",
    "recommend",
    "inbox",
    "chat",
    "geek",
    "resume",
    "labels",
}
BATCH_ACTIONS = {("batch-greet",), ("recruiter", "batch-view")}


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def normalized_command(arguments: Sequence[str]) -> tuple[str, ...]:
    values = tuple(item for item in arguments if item != "--")
    if not values:
        return ()
    return values


def classify(arguments: Sequence[str]) -> str:
    command = normalized_command(arguments)
    if not command:
        return "read"

    if command[0] in TOP_LEVEL_REMOTE_WRITES:
        return "remote-write"
    if command[0] in TOP_LEVEL_LOCAL_WRITES:
        return "local-write"
    if command[0] in TOP_LEVEL_READS:
        return "read"
    if command[0] == "recruiter" and len(command) == 1:
        return "read"
    if command[0] == "recruiter" and len(command) >= 2:
        if command[1] in RECRUITER_REMOTE_WRITES:
            return "remote-write"
        if command[1] in RECRUITER_LOCAL_WRITES:
            return "local-write"
        if command[1] in RECRUITER_READS:
            return "read"
    return "unknown"


def is_batch(arguments: Sequence[str]) -> bool:
    command = normalized_command(arguments)
    return command[:1] in BATCH_ACTIONS or command[:2] in BATCH_ACTIONS


def is_dry_run(arguments: Sequence[str]) -> bool:
    return "--dry-run" in normalized_command(arguments)


def validate(arguments: Sequence[str], confirm_write: bool, allow_batch: bool) -> str | None:
    command = normalized_command(arguments)
    if not command:
        return "缺少 boss 命令。"

    action_type = classify(command)
    if action_type == "unknown":
        return "已阻止未知命令。先检查当前 Skill 文档和 boss --help，不要把未知命令当作只读操作。"
    if action_type in {"remote-write", "local-write"} and not confirm_write:
        return (
            f"已阻止 {action_type} 操作。向用户展示准确对象与内容并取得明确确认后，"
            "重新执行并添加 --confirm-write。"
        )

    if is_batch(command) and not is_dry_run(command) and not allow_batch:
        return "已阻止批量操作。先执行 --dry-run；用户再次确认后添加 --allow-batch。"

    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安全调用 boss-cli")
    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="确认用户已批准当前写操作",
    )
    parser.add_argument(
        "--allow-batch",
        action="store_true",
        help="确认已预览并再次批准当前批量操作",
    )
    parser.add_argument("boss_args", nargs=argparse.REMAINDER, help="传递给 boss-cli 的参数")
    return parser


def main() -> int:
    configure_utf8_console()
    args = build_parser().parse_args()
    command = normalized_command(args.boss_args)
    error = validate(command, args.confirm_write, args.allow_batch)
    if error:
        print(error, file=sys.stderr)
        return 2

    executable = boss_executable()
    python_executable = runtime_python()
    compatibility_entrypoint = Path(__file__).with_name("boss_cli_compat.py")
    if not executable.is_file() or not python_executable.is_file():
        print(
            "尚未安装隔离运行时。请先执行：python scripts/bootstrap.py install",
            file=sys.stderr,
        )
        return 3
    if not compatibility_entrypoint.is_file():
        print("缺少 BOSS CLI 兼容入口，无法安全启动。", file=sys.stderr)
        return 4

    try:
        environment = os.environ.copy()
        environment.setdefault("PYTHONUTF8", "1")
        environment.setdefault("PYTHONIOENCODING", "utf-8")
        completed = subprocess.run(
            [str(python_executable), str(compatibility_entrypoint), *command],
            check=False,
            env=environment,
        )
    except OSError as exc:
        print(f"无法启动 boss-cli：{exc}", file=sys.stderr)
        return 5
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
