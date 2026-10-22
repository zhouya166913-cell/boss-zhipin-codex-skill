from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("inbox_monitor", SCRIPTS / "inbox_monitor.py")
assert SPEC and SPEC.loader
MONITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MONITOR)


def sample_payload(text: str, last_time: str = "10:00", *, is_self: bool = False) -> dict:
    return {
        "ok": True,
        "schema_version": "1",
        "data": {
            "friendList": [
                {
                    "uid": 1001,
                    "friendId": 2001,
                    "encryptUid": "candidate-1",
                    "name": "候选人甲",
                    "jobName": "AI 产品经理",
                    "encryptJobId": "job-1",
                }
            ],
            "lastMessages": [
                {
                    "uid": 1001,
                    "lastTime": last_time,
                    "lastMsgInfo": {"showText": text, "isSelf": is_self},
                }
            ],
        },
    }


class SnapshotTests(unittest.TestCase):
    def test_extracts_event_fields_and_direction(self) -> None:
        snapshot = MONITOR.extract_snapshot(sample_payload("请问工作地点在哪里？"))
        item = snapshot["2001"]
        self.assertEqual(item["friend_id"], 2001)
        self.assertEqual(item["candidate_name"], "候选人甲")
        self.assertEqual(item["job_name"], "AI 产品经理")
        self.assertEqual(item["direction"], "incoming")

    def test_baseline_does_not_emit_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite3"
            with MONITOR.connect_state(path) as connection:
                baseline, events = MONITOR.record_snapshot(
                    connection, MONITOR.extract_snapshot(sample_payload("历史消息"))
                )
            self.assertTrue(baseline)
            self.assertEqual(events, [])

    def test_changed_message_emits_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite3"
            with MONITOR.connect_state(path) as connection:
                MONITOR.record_snapshot(connection, MONITOR.extract_snapshot(sample_payload("旧消息")))
                baseline, events = MONITOR.record_snapshot(
                    connection,
                    MONITOR.extract_snapshot(sample_payload("新消息", "10:01")),
                )
                _, repeated = MONITOR.record_snapshot(
                    connection,
                    MONITOR.extract_snapshot(sample_payload("新消息", "10:01")),
                )
            self.assertFalse(baseline)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["last_text"], "新消息")
            self.assertEqual(repeated, [])

    def test_database_does_not_store_message_or_candidate_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite3"
            payload = sample_payload("这是不应写入数据库的敏感消息")
            with MONITOR.connect_state(path) as connection:
                MONITOR.record_snapshot(connection, MONITOR.extract_snapshot(payload))
                columns = [row[1] for row in connection.execute("PRAGMA table_info(conversations)")]
            self.assertEqual(columns, ["conversation_key", "fingerprint", "seen_at"])
            database_bytes = path.read_bytes()
            self.assertNotIn("敏感消息".encode("utf-8"), database_bytes)
            self.assertNotIn("候选人甲".encode("utf-8"), database_bytes)

    def test_minimum_interval_is_enforced(self) -> None:
        self.assertEqual(MONITOR.interval_value("30"), 30)
        with self.assertRaises(Exception):
            MONITOR.interval_value("10")


if __name__ == "__main__":
    unittest.main()
