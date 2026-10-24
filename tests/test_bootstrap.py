from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("bootstrap", SCRIPTS / "bootstrap.py")
assert SPEC and SPEC.loader
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOTSTRAP)


class BootstrapTests(unittest.TestCase):
    def test_runtime_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {BOOTSTRAP.RUNTIME_ENV: directory}):
                self.assertEqual(BOOTSTRAP.runtime_root(), Path(directory).resolve())

    def test_status_does_not_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {BOOTSTRAP.RUNTIME_ENV: directory}):
                payload = BOOTSTRAP.status_payload()
                self.assertFalse(payload["installed"])
                self.assertFalse(payload["recruiter_available"])
                self.assertFalse(payload["ready"])
                self.assertEqual(payload["state"], "runtime_missing")
                self.assertEqual(payload["next_action"], "install_runtime")
                self.assertEqual(payload["package"], BOOTSTRAP.PACKAGE_SPEC)
                self.assertIn(BOOTSTRAP.UPSTREAM_COMMIT, BOOTSTRAP.PACKAGE_SPEC)
                self.assertFalse((Path(directory) / "venv").exists())

    def test_readiness_state_is_explicit(self) -> None:
        self.assertEqual(
            BOOTSTRAP.readiness_state(False, False, False),
            ("python_unsupported", "prepare_python"),
        )
        self.assertEqual(
            BOOTSTRAP.readiness_state(True, True, False),
            ("runtime_incomplete", "reinstall_runtime"),
        )
        self.assertEqual(
            BOOTSTRAP.readiness_state(True, True, True),
            ("local_ready", "confirm_account_safety"),
        )

    def test_recruiter_probe_decodes_cli_output_as_utf8(self) -> None:
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="招聘方操作\nCommands:\n  resume  查看简历\n",
            stderr="",
        )
        with patch.object(BOOTSTRAP.subprocess, "run", return_value=result) as run:
            self.assertTrue(BOOTSTRAP.recruiter_available(Path(BOOTSTRAP.__file__)))

        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")


if __name__ == "__main__":
    unittest.main()
