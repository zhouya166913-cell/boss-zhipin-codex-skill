#!/usr/bin/env python3
"""Poll the recruiter inbox and emit deduplicated conversation-change events."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from typing import Any, Iterator

from bootstrap import boss_executable, configure_utf8_console, runtime_root


MIN_INTERVAL_SECONDS = 30
DEFAULT_INTERVAL_SECONDS = 60


class MonitorError(RuntimeError):
    pass


def default_state_path() -> Path:
    return runtime_root() / "monitor" / "inbox-state.sqlite3"


@contextmanager
def connect_state(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_key TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                seen_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.commit()
        yield connection
    finally:
        connection.close()


def metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_metadata(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO metadata(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _message_text(message: dict[str, Any]) -> str:
    info = message.get("lastMsgInfo")
    if not isinstance(info, dict):
        info = {}
    value = _first(info, "showText", "text", "content")
    if value is None:
        value = _first(message, "showText", "text", "content")
    if isinstance(value, dict):
        value = _first(value, "text", "showText")
    return str(value or "").strip()


def _direction(message: dict[str, Any]) -> str:
    info = message.get("lastMsgInfo")
    if not isinstance(info, dict):
        info = {}
    for mapping in (info, message):
        if "isSelf" in mapping:
            return "outgoing" if bool(mapping["isSelf"]) else "incoming"
        if "received" in mapping:
            return "incoming" if bool(mapping["received"]) else "outgoing"
    return "unknown"


def unwrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("ok") is False:
        error = payload.get("error")
        raise MonitorError(f"BOSS inbox 返回错误：{error}")
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise MonitorError("BOSS inbox 返回的数据结构不是对象。")
    return data


def extract_snapshot(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data = unwrap_payload(payload)
    friends = data.get("friendList", [])
    messages = data.get("lastMessages", [])
    if not isinstance(friends, list) or not isinstance(messages, list):
        raise MonitorError("BOSS inbox 缺少 friendList 或 lastMessages 列表。")

    friend_index: dict[str, dict[str, Any]] = {}
    for item in friends:
        if not isinstance(item, dict):
            continue
        for key in ("uid", "friendId", "encryptUid", "encryptFriendId"):
            value = item.get(key)
            if value not in (None, ""):
                friend_index[str(value)] = item

    snapshot: dict[str, dict[str, Any]] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        identity = _first(message, "uid", "friendId", "encryptUid", "id")
        if identity is None:
            continue
        identity_key = str(identity)
        friend = friend_index.get(identity_key, {})
        friend_id = _first(friend, "friendId") or _first(message, "friendId", "uid")
        conversation_key = str(friend_id or identity_key)
        text = _message_text(message)
        last_time = str(_first(message, "lastTime", "time", "timestamp") or "")
        fingerprint_source = {
            "identity": identity_key,
            "friend_id": friend_id,
            "last_time": last_time,
            "text": text,
            "direction": _direction(message),
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        snapshot[conversation_key] = {
            "conversation_key": conversation_key,
            "fingerprint": fingerprint,
            "friend_id": friend_id,
            "candidate_id": _first(friend, "encryptUid", "encryptFriendId"),
            "candidate_name": str(_first(friend, "name") or ""),
            "job_name": str(_first(friend, "jobName") or ""),
            "job_id": _first(friend, "encryptJobId", "jobId"),
            "last_text": text,
            "last_time": last_time,
            "direction": fingerprint_source["direction"],
        }
    return snapshot


def record_snapshot(
    connection: sqlite3.Connection,
    snapshot: dict[str, dict[str, Any]],
) -> tuple[bool, list[dict[str, Any]]]:
    initialized = metadata_value(connection, "initialized") == "1"
    now = datetime.now(timezone.utc).isoformat()
    events: list[dict[str, Any]] = []

    for key, item in snapshot.items():
        row = connection.execute(
            "SELECT fingerprint FROM conversations WHERE conversation_key = ?",
            (key,),
        ).fetchone()
        changed = row is None or row[0] != item["fingerprint"]
        if initialized and changed:
            event = {name: value for name, value in item.items() if name != "fingerprint"}
            event["event"] = "conversation_changed"
            events.append(event)
        connection.execute(
            "INSERT INTO conversations(conversation_key, fingerprint, seen_at) VALUES(?, ?, ?) "
            "ON CONFLICT(conversation_key) DO UPDATE SET "
            "fingerprint = excluded.fingerprint, seen_at = excluded.seen_at",
            (key, item["fingerprint"], now),
        )

    if not initialized:
        set_metadata(connection, "initialized", "1")
        set_metadata(connection, "baseline_at", now)
    set_metadata(connection, "last_poll_at", now)
    connection.commit()
    return not initialized, events


def fetch_inbox(job_id: str = "", timeout: int = 90) -> dict[str, Any]:
    executable = boss_executable()
    if not executable.is_file():
        raise MonitorError("尚未安装运行时，请先执行 scripts/bootstrap.py install。")
    command = [str(executable), "recruiter", "inbox", "--limit", "0", "--json"]
    if job_id:
        command.extend(["--job", job_id])
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    environment.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MonitorError(f"无法读取 BOSS inbox：{exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise MonitorError(f"BOSS inbox 命令失败（{result.returncode}）：{detail}")
    try:
        payload = json.loads(result.stdout.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise MonitorError("BOSS inbox 没有返回有效 JSON。") from exc
    if not isinstance(payload, dict):
        raise MonitorError("BOSS inbox JSON 顶层不是对象。")
    return payload


def poll_once(state_path: Path, job_id: str = "") -> dict[str, Any]:
    payload = fetch_inbox(job_id=job_id)
    snapshot = extract_snapshot(payload)
    with connect_state(state_path) as connection:
        baseline, events = record_snapshot(connection, snapshot)
    return {
        "ok": True,
        "event": "baseline" if baseline else "poll",
        "conversation_count": len(snapshot),
        "new_event_count": len(events),
        "events": events,
        "state_path": str(state_path),
    }


def interval_value(raw: str) -> int:
    value = int(raw)
    if value < MIN_INTERVAL_SECONDS:
        raise argparse.ArgumentTypeError(f"轮询间隔不能低于 {MIN_INTERVAL_SECONDS} 秒")
    return value


def state_status(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"ok": True, "initialized": False, "conversation_count": 0, "state_path": str(state_path)}
    with connect_state(state_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        return {
            "ok": True,
            "initialized": metadata_value(connection, "initialized") == "1",
            "conversation_count": count,
            "baseline_at": metadata_value(connection, "baseline_at"),
            "last_poll_at": metadata_value(connection, "last_poll_at"),
            "state_path": str(state_path),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="监听 BOSS 招聘端沟通列表变化")
    parser.add_argument("--state", type=Path, default=default_state_path(), help="本地去重状态数据库")
    subparsers = parser.add_subparsers(dest="action", required=True)

    check = subparsers.add_parser("check", help="检查一次并输出新事件")
    check.add_argument("--job", default="", help="只监听指定岗位 encryptJobId")

    watch = subparsers.add_parser("watch", help="持续轮询并以 NDJSON 输出事件")
    watch.add_argument("--job", default="", help="只监听指定岗位 encryptJobId")
    watch.add_argument("--interval", type=interval_value, default=DEFAULT_INTERVAL_SECONDS)
    watch.add_argument("--runs", type=int, default=0, help="轮询次数，0 表示持续运行")

    subparsers.add_parser("status", help="查看本地监听状态，不访问 BOSS")
    return parser


def main() -> int:
    configure_utf8_console()
    args = build_parser().parse_args()
    state_path = args.state.expanduser().resolve()

    if args.action == "status":
        print(json.dumps(state_status(state_path), ensure_ascii=False, indent=2))
        return 0

    if args.action == "check":
        try:
            result = poll_once(state_path, job_id=args.job)
        except MonitorError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    completed_runs = 0
    consecutive_errors = 0
    while args.runs == 0 or completed_runs < args.runs:
        try:
            result = poll_once(state_path, job_id=args.job)
            consecutive_errors = 0
            if result["event"] == "baseline":
                print(json.dumps(result, ensure_ascii=False), flush=True)
            else:
                for event in result["events"]:
                    print(json.dumps(event, ensure_ascii=False), flush=True)
        except MonitorError as exc:
            consecutive_errors += 1
            print(json.dumps({"ok": False, "event": "error", "error": str(exc)}, ensure_ascii=False), flush=True)
            if consecutive_errors >= 3:
                return 1
        completed_runs += 1
        if args.runs == 0 or completed_runs < args.runs:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
