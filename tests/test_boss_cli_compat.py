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
            def _headers_for_request(self, url, params=None):
                return {"Referer": "https://www.zhipin.com/"}

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


class RecruiterGreetingCompatibilityTests(unittest.TestCase):
    def test_recommend_params_bind_job_and_page_without_narrowing_filters(self) -> None:
        params = BOSS_CLI_COMPAT.build_recommend_params("job-token", page=2)
        self.assertEqual(params["jobId"], "job-token")
        self.assertEqual(params["page"], 2)
        self.assertEqual(params["gender"], 0)
        self.assertEqual(params["experience"], 0)
        self.assertEqual(params["degree"], 0)

    def test_recommend_requires_a_unique_job(self) -> None:
        with self.assertRaises(ValueError):
            BOSS_CLI_COMPAT.build_recommend_params("")

    def test_chat_start_requires_a_session_identifier_for_success(self) -> None:
        self.assertTrue(BOSS_CLI_COMPAT.chat_start_confirmed({"geekId": 456}))
        self.assertFalse(BOSS_CLI_COMPAT.chat_start_confirmed({"newfriend": 1}))
        self.assertFalse(BOSS_CLI_COMPAT.chat_start_confirmed(None))

    def test_chat_start_payload_matches_recruiter_web_request(self) -> None:
        self.assertEqual(
            BOSS_CLI_COMPAT.build_chat_start_payload(
                "geek-token",
                "job-token",
                "security-token",
                expect_id=123,
                lid="recommend-link",
                message="你好，想和你聊聊这个岗位。",
            ),
            {
                "gid": "geek-token",
                "suid": "",
                "jid": "job-token",
                "expectId": "123",
                "lid": "recommend-link",
                "greet": "你好，想和你聊聊这个岗位。",
                "from": "",
                "securityId": "security-token",
                "customGreetingGuide": "-1",
            },
        )

    def test_patch_adds_real_chat_start_and_referer(self) -> None:
        class FakeBossClient:
            def _headers_for_request(self, url, params=None):
                return {"Referer": "https://www.zhipin.com/"}

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
        instance._post = Mock(return_value={"geekId": 456, "newfriend": 1})
        result = instance.boss_chat_start(
            "geek-token",
            "job-token",
            "security-token",
            expect_id="123",
            lid="recommend-link",
            message="你好",
        )

        self.assertEqual(result, {"geekId": 456, "newfriend": 1})
        instance._post.assert_called_once_with(
            BOSS_CLI_COMPAT.CHAT_START_URL,
            data=BOSS_CLI_COMPAT.build_chat_start_payload(
                "geek-token",
                "job-token",
                "security-token",
                "123",
                "recommend-link",
                "你好",
            ),
            action="打招呼",
        )
        self.assertEqual(
            instance._headers_for_request(BOSS_CLI_COMPAT.CHAT_START_URL)["Referer"],
            BOSS_CLI_COMPAT.CHAT_START_REFERER,
        )

        instance._get = Mock(return_value={"geekList": [], "hasMore": False})
        self.assertEqual(
            instance.get_boss_recommend_geeks(page=3, enc_job_id="job-token"),
            {"geekList": [], "hasMore": False},
        )
        instance._get.assert_called_once_with(
            BOSS_CLI_COMPAT.RECOMMEND_GEEKS_URL,
            params=BOSS_CLI_COMPAT.build_recommend_params("job-token", 3),
            action="推荐牛人",
        )
        self.assertEqual(
            instance._headers_for_request(BOSS_CLI_COMPAT.RECOMMEND_GEEKS_URL)["Referer"],
            BOSS_CLI_COMPAT.CHAT_START_REFERER,
        )


if __name__ == "__main__":
    unittest.main()
