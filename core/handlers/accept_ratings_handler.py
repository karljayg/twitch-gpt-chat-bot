import asyncio
import logging

from core.command_service import CommandContext, ICommandHandler
from core import fsl_chat_voting as fcv
from settings import config

logger = logging.getLogger(__name__)


def _allowed(author: str) -> bool:
    a = author.lower()
    allowed = {
        config.PAGE.lower(),
        config.OWNER.lower(),
        config.USERNAME.lower(),
        config.STREAMER_NICKNAME.lower(),
    }
    extra = getattr(config, "FSL_RATINGS_ADMIN_LOGINS", None) or []
    for x in extra:
        allowed.add(str(x).lower())
    return a in allowed


class AcceptRatingsHandler(ICommandHandler):
    """accept ratings <fsl_match_id> — opens FSL voting window and captures chat tokens."""

    def __init__(self, twitch_bot):
        self.twitch_bot = twitch_bot

    async def handle(self, context: CommandContext, args: str):
        if not getattr(config, "ENABLE_FSL_CHAT_VOTING", False):
            await context.chat_service.send_message(
                context.channel, "FSL chat voting is disabled (config)."
            )
            return
        if not _allowed(context.author):
            await context.chat_service.send_message(
                context.channel, "Only the streamer/mod can start ratings."
            )
            return
        parts = (args or "").strip().split()
        mid: int | None = None
        if parts:
            try:
                mid = int(parts[0])
            except ValueError:
                await context.chat_service.send_message(
                    context.channel, "Invalid match id (integer required)."
                )
                return
        else:
            tid = getattr(config, "FSL_TUNNEL_TEST_MATCH_ID", None)
            if tid is not None:
                mid = int(tid)
            else:
                await context.chat_service.send_message(
                    context.channel,
                    "Usage: accept ratings <fsl_match_id> (or set FSL_TUNNEL_TEST_MATCH_ID for default).",
                )
                return

        tb = self.twitch_bot
        if getattr(tb, "fsl_voting_session", None) and tb.fsl_voting_session.is_active():
            await context.chat_service.send_message(
                context.channel,
                "A ratings session is already active. Type: end ratings",
            )
            return

        loop = asyncio.get_running_loop()
        mdata, err = await loop.run_in_executor(None, fcv.api_get_match, mid)
        if err or not mdata:
            await context.chat_service.send_message(
                context.channel, f"Ratings: match lookup failed: {err}"
            )
            return

        def _enable():
            return fcv.api_post_enable(
                mid, context.author, getattr(config, "PAGE", "") or ""
            )

        ena, err2 = await loop.run_in_executor(None, _enable)
        if err2 or not ena:
            await context.chat_service.send_message(
                context.channel, f"Ratings: enable failed: {err2}"
            )
            return

        p1 = mdata.get("player1", {}).get("real_name", "?")
        p2 = mdata.get("player2", {}).get("real_name", "?")
        session = fcv.FSLChatVotingSession(
            fsl_match_id=mid,
            session_id=int(ena["session_id"]),
            expires_at_iso=str(ena.get("expires_at", "")),
            player1_name=p1,
            player2_name=p2,
            twitch_bot=tb,
        )
        tb.fsl_voting_session = session
        session.schedule_auto_submit()
        logger.info(
            f"[FSL voting] Session started match={mid} session={ena.get('session_id')} by {context.author}"
        )
        await context.chat_service.send_message(
            context.channel,
            fcv.clip_chat_message(fcv.short_ratings_open_message(p1, p2)),
        )


class RatingsHelpHandler(ICommandHandler):
    """!ratings — full voting help once per active session (avoids spam)."""

    def __init__(self, twitch_bot):
        self.twitch_bot = twitch_bot

    async def handle(self, context: CommandContext, args: str):
        if not getattr(config, "ENABLE_FSL_CHAT_VOTING", False):
            return
        sess = getattr(self.twitch_bot, "fsl_voting_session", None)
        if not sess or not sess.is_active():
            await context.chat_service.send_message(
                context.channel,
                "No ratings window is open. (Mods: accept ratings <match id> when ready.)",
            )
            return
        if not sess.try_claim_long_help():
            await context.chat_service.send_message(
                context.channel,
                "Full !ratings instructions were already posted this round — scroll up.",
            )
            return
        for chunk in fcv.long_ratings_help_chunks(sess.player1_name, sess.player2_name):
            await context.chat_service.send_message(context.channel, chunk)


class EndRatingsHandler(ICommandHandler):
    """end ratings — submit tallies now (mod)."""

    def __init__(self, twitch_bot):
        self.twitch_bot = twitch_bot

    async def handle(self, context: CommandContext, args: str):
        if not getattr(config, "ENABLE_FSL_CHAT_VOTING", False):
            return
        if not _allowed(context.author):
            await context.chat_service.send_message(
                context.channel, "Only the streamer/mod can end ratings."
            )
            return
        sess = getattr(self.twitch_bot, "fsl_voting_session", None)
        if not sess or not sess.is_active():
            await context.chat_service.send_message(
                context.channel, "No active ratings session."
            )
            return
        reason = f"mod {context.author}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sess.submit_final, reason)
        # submit_final posts summary to chat and clears fsl_voting_session
