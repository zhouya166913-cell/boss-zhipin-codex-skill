from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("boss_safe", SCRIPTS / "boss_safe.py")
assert SPEC and SPEC.loader
BOSS_SAFE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOSS_SAFE)


class ClassificationTests(unittest.TestCase):
    def test_recruiter_reads_are_allowed(self) -> None:
        for command in (
            ["recruiter", "jobs", "--json"],
            ["recruiter", "search", "Python", "--json"],
            ["recruiter", "resume", "candidate", "--job", "job", "--json"],
        ):
            self.assertEqual(BOSS_SAFE.classify(command), "read")
            self.assertIsNone(BOSS_SAFE.validate(command, False, False))

    def test_remote_write_requires_confirmation(self) -> None:
        command = ["recruiter", "reply", "123", "你好"]
        self.assertEqual(BOSS_SAFE.classify(command), "remote-write")
        self.assertIsNotNone(BOSS_SAFE.validate(command, False, False))
        self.assertIsNone(BOSS_SAFE.validate(command, True, False))

    def test_all_known_remote_writes_are_guarded(self) -> None:
        top_level = [[name, "target"] for name in BOSS_SAFE.TOP_LEVEL_REMOTE_WRITES]
        recruiter = [["recruiter", name, "target"] for name in BOSS_SAFE.RECRUITER_REMOTE_WRITES]
        for command in top_level + recruiter:
            self.assertEqual(BOSS_SAFE.classify(command), "remote-write", command)
            self.assertIsNotNone(BOSS_SAFE.validate(command, False, False), command)

    def test_local_export_requires_confirmation(self) -> None:
        command = ["recruiter", "export", "-o", "candidates.json"]
        self.assertEqual(BOSS_SAFE.classify(command), "local-write")
        self.assertIsNotNone(BOSS_SAFE.validate(command, False, False))
        self.assertIsNone(BOSS_SAFE.validate(command, True, False))

    def test_batch_requires_dry_run_or_second_gate(self) -> None:
        command = ["batch-greet", "Python", "--yes"]
        self.assertIsNotNone(BOSS_SAFE.validate(command, True, False))
        self.assertIsNone(BOSS_SAFE.validate(["batch-greet", "Python", "--dry-run"], True, False))
        self.assertIsNone(BOSS_SAFE.validate(command, True, True))

    def test_separator_is_ignored(self) -> None:
        command = ["--", "recruiter", "job-close", "job"]
        self.assertEqual(BOSS_SAFE.classify(command), "remote-write")

    def test_unknown_commands_fail_closed(self) -> None:
        for command in (["future-command"], ["recruiter", "future-command"]):
            self.assertEqual(BOSS_SAFE.classify(command), "unknown")
            self.assertIsNotNone(BOSS_SAFE.validate(command, True, True))


if __name__ == "__main__":
    unittest.main()
