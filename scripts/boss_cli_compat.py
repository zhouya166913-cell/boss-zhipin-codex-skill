#!/usr/bin/env python3
"""Run boss-cli with compatibility fixes for the pinned upstream release."""

from __future__ import annotations

from typing import Any


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
    """Patch only the known-broken recruiter friend-list request."""
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


def main() -> None:
    apply_compatibility_patches()
    from boss_cli.cli import cli

    cli(prog_name="boss")


if __name__ == "__main__":
    main()
