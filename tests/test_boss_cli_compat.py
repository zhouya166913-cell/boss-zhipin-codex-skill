from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location(
    "boss_cli_compat", SCRIPTS / "boss_cli_compat.py"
)
assert SPEC and SPEC.loader
BOSS_CLI_COMPAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOSS_CLI_COMPAT)


class FriendListCompatibilityTests(unittest.TestCase):
    def test_payload_matches_current_web_client(self) -> None:
        self.assertEqual(
            BOSS_CLI_COMPAT.build_friend_list_payload(),
            {"labelId": 0, "encJobId": ""},
        )

    def test_payload_keeps_job_and_sort_but_never_legacy_page(self) -> None:
        payload = BOSS_CLI_COMPAT.build_friend_list_payload(
            label_id=2,
            enc_job_id="job-token",
            sort="recommend",
        )
        self.assertEqual(
            payload,
            {"labelId": 2, "encJobId": "job-token", "sort": "recommend"},
        )
        self.assertNotIn("page", payload)

    def test_patch_preserves_signature_but_drops_page_from_request(self) -> None:
        class FakeBossClient:
            pass

        client_module = types.ModuleType("boss_cli.client")
        client_module.BossClient = FakeBossClient
        constants_module = types.ModuleType("boss_cli.constants")
        constants_module.BOSS_FRIEND_LIST_URL = "/friend/list"

        with patch.dict(
            sys.modules,
            {
                "boss_cli": types.ModuleType("boss_cli"),
                "boss_cli.client": client_module,
                "boss_cli.constants": constants_module,
            },
        ):
            BOSS_CLI_COMPAT.apply_compatibility_patches()

        instance = FakeBossClient()
        instance._post = Mock(return_value={"result": []})
        result = instance.get_boss_friend_list(
            label_id=1,
            enc_job_id="job-token",
            sort="recent",
            page=9,
        )

        self.assertEqual(result, {"result": []})
        instance._post.assert_called_once_with(
            "/friend/list",
            data={"labelId": 1, "encJobId": "job-token", "sort": "recent"},
            action="候选人列表",
        )


if __name__ == "__main__":
    unittest.main()
