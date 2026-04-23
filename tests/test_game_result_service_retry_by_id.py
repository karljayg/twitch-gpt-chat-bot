import pytest
from unittest.mock import MagicMock

from core.game_result_service import GameResultService


class _TwitchServiceStub:
    def __init__(self, twitch_bot):
        self.twitch_bot = twitch_bot

    def get_platform_name(self):
        return "twitch"


@pytest.mark.asyncio
async def test_retry_by_replay_id_sets_followup_flags():
    replay_repo = MagicMock()
    db = MagicMock()
    replay_repo.db = db
    db.get_replay_by_id.return_value = {
        "replay_id": 25862,
        "replay_summary": "Players: Meteor: Terran, KJ: Protoss\nMeteor's Build Order (first set of steps):\nTime: 0:15, Name: SupplyDepot, Supply: 14\n",
        "opponent": "Meteor",
        "opponent_race": "Terran",
        "map": "White Rabbit LE",
        "date": "2026-04-21 21:31:57",
        "result": "Defeat",
        "duration": "12m 40s",
        "existing_comment": "",
    }

    twitch_bot = MagicMock()
    twitch_service = _TwitchServiceStub(twitch_bot)
    service = GameResultService(replay_repo, [twitch_service], pattern_learner=None)

    ok = await service._retry_by_replay_id(25862)
    assert ok is True
    args = twitch_bot._display_pattern_validation.call_args[0]
    game_data = args[0]
    assert game_data["force_followup_prompt"] is True
    assert game_data["suppress_followup_prompt"] is False
    assert game_data["suppress_pattern_validation_line"] is False
