"""Unit tests for FSL chat voting token parsing and tally aggregation."""
import unittest

from core.fsl_chat_voting import (
    FSLChatVotingSession,
    long_ratings_help_chunks,
    short_ratings_open_message,
)


class _FakeTwitch:
    fsl_voting_session = None

    def send_channel_message_sync(self, text: str) -> None:
        pass


class TestFSLChatVoting(unittest.TestCase):
    def test_consume_and_aggregate(self):
        tb = _FakeTwitch()
        s = FSLChatVotingSession(
            fsl_match_id=99,
            session_id=1,
            expires_at_iso="2099-01-01T00:00:00+00:00",
            player1_name="P1",
            player2_name="P2",
            twitch_bot=tb,
        )
        self.assertEqual(s.record_chat_line("alice", "mic1 mac2"), "consume")
        self.assertEqual(s.record_chat_line("bob", "mic2 mact"), "consume")
        s.cancel_timer()
        body = s.build_votes_body(reviewer_id=7)
        self.assertEqual(body["fsl_match_id"], 99)
        self.assertEqual(body["reviewer_id"], 7)
        micro = body["votes"]["micro"]
        self.assertEqual(micro["tally"]["player1"], 1)
        self.assertEqual(micro["tally"]["player2"], 1)
        self.assertEqual(micro["tally"]["tie"], 0)
        macro = body["votes"]["macro"]
        self.assertEqual(macro["tally"]["player1"], 0)
        self.assertEqual(macro["tally"]["player2"], 1)
        self.assertEqual(macro["tally"]["tie"], 1)

    def test_last_vote_wins(self):
        tb = _FakeTwitch()
        s = FSLChatVotingSession(
            fsl_match_id=1,
            session_id=1,
            expires_at_iso="2099-01-01T00:00:00+00:00",
            player1_name="A",
            player2_name="B",
            twitch_bot=tb,
        )
        s.record_chat_line("u1", "mic1")
        s.record_chat_line("u1", "mic2")
        s.cancel_timer()
        t = s.build_votes_body(1)["votes"]["micro"]["tally"]
        self.assertEqual(t["player1"], 0)
        self.assertEqual(t["player2"], 1)

    def test_short_ratings_open_message_mentions_players_and_ratings(self):
        s = short_ratings_open_message("Freeedom", "SirMalagant")
        self.assertIn("Freeedom(P1)", s)
        self.assertIn("SirMalagant(P2)", s)
        self.assertIn("mic=micro", s)
        self.assertIn("!ratings", s)

    def test_try_claim_long_help_once(self):
        tb = _FakeTwitch()
        s = FSLChatVotingSession(
            fsl_match_id=1,
            session_id=1,
            expires_at_iso="2099-01-01T00:00:00+00:00",
            player1_name="A",
            player2_name="B",
            twitch_bot=tb,
        )
        self.assertTrue(s.try_claim_long_help())
        self.assertFalse(s.try_claim_long_help())

    def test_long_ratings_help_chunks_non_empty(self):
        chunks = long_ratings_help_chunks("X", "Y")
        self.assertGreaterEqual(len(chunks), 1)
        blob = "\n".join(chunks).lower()
        self.assertIn("spider chart", blob)
        self.assertIn("ratings open", blob)
        self.assertIn("mic1", blob)


if __name__ == "__main__":
    unittest.main()
