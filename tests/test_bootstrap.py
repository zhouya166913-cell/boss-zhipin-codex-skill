from __future__ import annotations

import importlib.util
import os
from pathlib import Path
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
                self.assertEqual(payload["package"], BOOTSTRAP.PACKAGE_SPEC)
                self.assertIn(BOOTSTRAP.UPSTREAM_COMMIT, BOOTSTRAP.PACKAGE_SPEC)
                self.assertFalse((Path(directory) / "venv").exists())


if __name__ == "__main__":
    unittest.main()
