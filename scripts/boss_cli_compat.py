#!/usr/bin/env python3
"""Run boss-cli with compatibility fixes for the pinned upstream release."""

from __future__ import annotations

from typing import Any


# Request shapes are adapted from jackwener/boss-cli PR #29 commits
# bcd477e and a32839b, then covered by this repository's own regression tests.
CHAT_START_URL = "/wapi/zpjob/chat/start"
CHAT_START_REFERER = "https://www.zhipin.com/web/frame/recommend/"
RECOMMEND_GEEKS_URL = "/wapi/zpjob/rec/geek/list"


def build_chat_start_payload(
    encrypt_geek_id: str,
    encrypt_job_id: str,
    security_id: str,
    expect_id: int | str = "",
    lid: str = "",
    message: str = "",
) -> dict[str, str]:
    """Build the recruiter web client's real "start chat" request body."""
    return {
        "gid": encrypt_geek_id,
        "suid": "",
        "jid": encrypt_job_id,
        "expectId": str(expect_id) if expect_id else "",
        "lid": lid,
        "greet": message,
        "from": "",
        "securityId": security_id,
        "customGreetingGuide": "-1",
    }


def build_recommend_params(encrypt_job_id: str, page: int = 1) -> dict[str, Any]:
    """Build the unfiltered recruiter "recommended candidates" request."""
    if not encrypt_job_id:
        raise ValueError("推荐候选人必须绑定唯一岗位。")
    return {
        "age": "16,-1",
        "school": 0,
        "activation": 0,
        "gender": 0,
        "recentNotView": 0,
        "exchangeResumeWithColleague": 0,
        "major": 0,
        "keyword1": -1,
        "switchJobFrequency": 0,
        "experience": 0,
        "degree": 0,
        "intention": 0,
        "salary": 0,
        "jobId": encrypt_job_id,
        "page": page,
        "coverScreenMemory": 0,
        "cardType": 0,
    }


def chat_start_confirmed(data: object) -> bool:
    """Return true only when BOSS returned a usable chat-session identifier."""
    return isinstance(data, dict) and bool(data.get("geekId"))


def build_friend_list_payload(
    label_id: int = 0,
    enc_job_id: str = "",
    sort: str = "",
) -> dict[str, Any]:
    """Build the payload currently used by the BOSS recruiter chat page.

    The pinned upstream release sends a ``page`` field and omits an empty
    ``encJobId``. The current web client does the opposite; sending the old
    payload can make ``filterByLabel`` fail with BOSS business code 1093.
    """
    payload: dict[str, Any] = {
        "labelId": label_id,
        "encJobId": enc_job_id,
    }
    if sort:
        payload["sort"] = sort
    return payload


def apply_compatibility_patches() -> None:
    """Patch known-broken recruiter requests in the pinned upstream CLI."""
    from boss_cli.client import BossClient
    from boss_cli.constants import BOSS_FRIEND_LIST_URL

    def get_boss_friend_list(
        self: Any,
        label_id: int = 0,
        enc_job_id: str = "",
        sort: str = "",
        page: int = 1,
    ) -> dict[str, Any]:
        # Keep ``page`` in the signature for compatibility with the pinned
        # client, but do not send it: the current web endpoint returns the
        # complete filtered list and rejects the legacy pagination payload.
        del page
        return self._post(
            BOSS_FRIEND_LIST_URL,
            data=build_friend_list_payload(label_id, enc_job_id, sort),
            action="候选人列表",
        )

    BossClient.get_boss_friend_list = get_boss_friend_list

    def boss_chat_start(
        self: Any,
        encrypt_geek_id: str,
        encrypt_job_id: str,
        security_id: str,
        expect_id: int | str = "",
        lid: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        return self._post(
            CHAT_START_URL,
            data=build_chat_start_payload(
                encrypt_geek_id,
                encrypt_job_id,
                security_id,
                expect_id,
                lid,
                message,
            ),
            action="打招呼",
        )

    BossClient.boss_chat_start = boss_chat_start

    def get_boss_recommend_geeks(
        self: Any,
        page: int = 1,
        enc_job_id: str = "",
    ) -> dict[str, Any]:
        return self._get(
            RECOMMEND_GEEKS_URL,
            params=build_recommend_params(enc_job_id, page),
            action="推荐牛人",
        )

    BossClient.get_boss_recommend_geeks = get_boss_recommend_geeks

    current_headers = BossClient._headers_for_request
    if not getattr(current_headers, "_boss_skill_chat_start", False):
        original_headers = current_headers

        def headers_for_request(
            self: Any,
            url: str,
            params: dict[str, Any] | None = None,
        ) -> dict[str, str]:
            headers = original_headers(self, url, params=params)
            if url in {CHAT_START_URL, RECOMMEND_GEEKS_URL}:
                headers["Referer"] = CHAT_START_REFERER
            return headers

        headers_for_request._boss_skill_chat_start = True  # type: ignore[attr-defined]
        BossClient._headers_for_request = headers_for_request


def apply_command_patches() -> None:
    """Replace the pinned recruiter's no-op greet command with a real send."""
    import click

    from boss_cli.client import BossClient
    from boss_cli.commands._common import (
        console,
        handle_command,
        require_auth,
        structured_output_options,
    )
    from boss_cli.commands.recruiter import recruiter
    from boss_cli.exceptions import BossApiError

    @click.command("recommend")
    @click.option("-n", "--limit", "display_limit", default=0, type=int, help="显示数量 (0=全部)")
    @click.option("-p", "--page", default=1, type=int, help="页码 (默认: 1, 每页约 15 人)")
    @click.option("--job", "enc_job_id", required=True, help="目标职位 encryptJobId (必填)")
    @structured_output_options
    def recruiter_recommend(
        display_limit: int,
        page: int,
        enc_job_id: str,
        as_json: bool,
        as_yaml: bool,
    ) -> None:
        """读取与网页“推荐牛人”一致的岗位候选人发现池。"""
        credential = require_auth()

        def action(client: BossClient) -> dict[str, Any]:
            return client.get_boss_recommend_geeks(page=page, enc_job_id=enc_job_id)

        def render(data: dict[str, Any]) -> None:
            candidates = data.get("geekList", [])
            if display_limit > 0:
                candidates = candidates[:display_limit]
            if not candidates:
                console.print("[yellow]当前岗位暂无推荐候选人。[/yellow]")
                return
            console.print(f"[cyan]推荐候选人第 {page} 页：{len(candidates)} 人[/cyan]")
            for index, item in enumerate(candidates, 1):
                card = item.get("geekCard", {}) if isinstance(item, dict) else {}
                if not isinstance(card, dict) or not card:
                    card = item if isinstance(item, dict) else {}
                name = card.get("geekName", "候选人")
                experience = card.get("workExpDesc") or card.get("geekWorkYear") or "经验待核实"
                city = card.get("cityName") or card.get("expectLocationName") or "地点待核实"
                console.print(f"  {index}. {name} · {experience} · {city}")
            if data.get("hasMore"):
                console.print(f"[dim]还有下一页，可继续读取第 {page + 1} 页。[/dim]")

        handle_command(
            credential,
            action=action,
            render=render,
            as_json=as_json,
            as_yaml=as_yaml,
        )

    @click.command("greet")
    @click.argument("encrypt_geek_id")
    @click.option("--job", "encrypt_job_id", required=True, help="目标职位 encryptJobId (必填)")
    @click.option(
        "--security-id",
        "security_id",
        required=True,
        help="候选人 securityId (从 recommend/search 结果获取)",
    )
    @click.option("--expect-id", "expect_id", default="", help="候选人 expectId (可选)")
    @click.option("--lid", default="", help="推荐链路 lid (可选)")
    @click.option("-m", "--message", "greet_message", default="", help="自定义首条消息")
    @structured_output_options
    def recruiter_greet(
        encrypt_geek_id: str,
        encrypt_job_id: str,
        security_id: str,
        expect_id: str,
        lid: str,
        greet_message: str,
        as_json: bool,
        as_yaml: bool,
    ) -> None:
        """真正发起候选人沟通，并可同时发送定制首条消息。"""
        credential = require_auth()

        def action(client: BossClient) -> dict[str, Any]:
            data = client.boss_chat_start(
                encrypt_geek_id=encrypt_geek_id,
                encrypt_job_id=encrypt_job_id,
                security_id=security_id,
                expect_id=expect_id,
                lid=lid,
                message=greet_message,
            )
            if not chat_start_confirmed(data):
                raise BossApiError(
                    "打招呼接口未返回会话标识，无法确认发送成功；已停止后续发送。"
                )
            return data

        def render(data: dict[str, Any]) -> None:
            status = "新沟通" if str(data.get("newfriend")) == "1" else "已有沟通"
            console.print(f"[green]已完成真实打招呼[/green]  状态={status}")
            if greet_message:
                console.print("[dim]定制首条消息已随会话发出。[/dim]")

        handle_command(
            credential,
            action=action,
            render=render,
            as_json=as_json,
            as_yaml=as_yaml,
        )

    recruiter.commands["recommend"] = recruiter_recommend
    recruiter.commands["greet"] = recruiter_greet


def main() -> None:
    apply_compatibility_patches()
    apply_command_patches()
    from boss_cli.cli import cli

    cli(prog_name="boss")


if __name__ == "__main__":
    main()
