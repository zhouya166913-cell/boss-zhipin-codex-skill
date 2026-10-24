from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("boss_safe", SCRIPTS / "boss_safe.py")
assert SPEC and SPEC.loader
BOSS_SAFE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOSS_SAFE)


class ClassificationTests(unittest.TestCase):
    def test_login_requires_explicit_auth_confirmation(self) -> None:
        command = ["login", "--qrcode"]
        self.assertEqual(BOSS_SAFE.classify(command), "auth")
        self.assertIsNotNone(BOSS_SAFE.validate(command, False, False))
        self.assertIsNone(BOSS_SAFE.validate(command, False, False, True))

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


class EntrypointTests(unittest.TestCase):
    def test_main_runs_cli_through_compatibility_entrypoint(self) -> None:
        fake_completed = Mock(returncode=0)
        scripts = Path(BOSS_SAFE.__file__).resolve().parent
        with (
            patch.object(BOSS_SAFE, "boss_executable", return_value=scripts / "boss_safe.py"),
            patch.object(BOSS_SAFE, "runtime_python", return_value=Path(sys.executable)),
            patch.object(BOSS_SAFE, "build_parser") as build_parser,
            patch.object(BOSS_SAFE.subprocess, "run", return_value=fake_completed) as run,
        ):
            build_parser.return_value.parse_args.return_value = Mock(
                boss_args=["recruiter", "inbox", "--json"],
                confirm_auth=False,
                confirm_write=False,
                allow_batch=False,
            )
            self.assertEqual(BOSS_SAFE.main(), 0)

        invoked = run.call_args.args[0]
        self.assertEqual(invoked[0], sys.executable)
        self.assertEqual(Path(invoked[1]).name, "boss_cli_compat.py")
        self.assertEqual(invoked[2:], ["recruiter", "inbox", "--json"])


if __name__ == "__main__":
    unittest.main()
