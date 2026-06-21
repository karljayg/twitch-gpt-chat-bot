"""Unit tests for Stream Production coalescing/reduction (anti-spam) logic.

These are pure logic tests: time is injected, no network or LLM.
"""
import unittest

from core.stream_production.models import StatusSnapshot, StreamEvent
from core.stream_production.coalescer import (
    EventCoalescer,
    Reducer,
    FlushBatch,
    format_featured_matchups,
    build_summary_prompt,
)


def _snapshot(seq=1, a_name="PulledTheBoys", b_name="Angry Space Hares",
              a_score=10, b_score=6, series_winner=None, scene="scoreboard",
              alive=True, events=None):
    return StatusSnapshot.from_json({
        "seq": seq,
        "stream_alive": alive,
        "heartbeat_age_ms": 100,
        "scene": {"active": scene, "label": scene, "previous": "sc2"},
        "music": {"mood": "hype", "mood_label": "Hype", "playing": True},
        "match": {
            "team_a": {"name": a_name, "score": a_score},
            "team_b": {"name": b_name, "score": b_score},
            "series_winner": series_winner,
        },
        "recent_events": events or [],
    })


def _ev(id_, type_, data, at="2026-06-20T20:00:00-04:00"):
    return StreamEvent.from_json({"id": id_, "at": at, "type": type_, "data": data})


class TestReducer(unittest.TestCase):
    def setUp(self):
        self.reducer = Reducer(meaningful_scenes=["pog", "scoreboard", "custom-scoreboard"])

    def test_collapses_multiple_score_events_to_net(self):
        snap = _snapshot(a_score=10, b_score=6)
        events = [
            _ev(1, "score", {"team": "a", "from": 8, "to": 9}),
            _ev(2, "score", {"team": "a", "from": 9, "to": 10}),
        ]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(len(lines), 1)
        self.assertIn("now 10", lines[0])
        self.assertIn("PulledTheBoys", lines[0])
        self.assertIn("10 - 6", lines[0])  # full team-league tally

    def test_noise_only_batch_is_not_significant(self):
        snap = _snapshot(scene="logos")
        events = [
            _ev(1, "connect", {"user": "producer"}),
            _ev(2, "music", {"mood": "chill"}),
            _ev(3, "scene", {"to": "logos", "from": "sc2"}),  # not a meaningful scene
        ]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(lines, [])

    def test_winner_line_uses_team_aggregate(self):
        snap = _snapshot(a_score=11, b_score=6, series_winner="PulledTheBoys")
        events = [_ev(5, "winner", {"team": "a", "name": "PulledTheBoys"})]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(len(lines), 1)
        self.assertIn("Series decided", lines[0])
        self.assertIn("PulledTheBoys", lines[0])
        self.assertIn("11-6", lines[0])

    def test_winner_suppresses_redundant_score_and_gg(self):
        snap = _snapshot(a_score=11, b_score=6, series_winner="PulledTheBoys")
        events = [
            _ev(1, "score", {"team": "a", "from": 10, "to": 11}),
            _ev(2, "gg", {"kind": "match_gg"}),
            _ev(3, "winner", {"team": "a", "name": "PulledTheBoys"}),
        ]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(len(lines), 1)
        self.assertIn("Series decided", lines[0])

    def test_lone_match_gg_is_not_significant(self):
        # A match-GG only means the final game finished; the series result comes from
        # the winner/series_winner, so a lone match-GG produces no line.
        snap = _snapshot()
        events = [_ev(1, "gg", {"kind": "match_gg"})]
        self.assertEqual(self.reducer.reduce(events, snap), [])

    def test_plain_gg_flash_is_not_significant(self):
        snap = _snapshot()
        events = [_ev(1, "gg", {"kind": "gg"})]
        self.assertEqual(self.reducer.reduce(events, snap), [])

    def test_bare_intro_without_gg_is_dropped(self):
        # Intros are only intros unless tied to a GG.
        snap = _snapshot()
        events = [_ev(1, "intro", {"player": "ChienPwn"})]
        self.assertEqual(self.reducer.reduce(events, snap), [])

    def test_intro_with_gg_is_spotlighted(self):
        snap = _snapshot()
        events = [_ev(1, "gg", {"kind": "gg"}), _ev(2, "intro", {"player": "ChienPwn"})]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(len(lines), 1)
        self.assertIn("ChienPwn", lines[0])

    def test_intro_classifies_player_vs_team(self):
        # Real feed: GG, then intro player Neutrophil, then intro team-name PulledTheBoys.
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming")
        events = [
            _ev(1, "gg", {"kind": "gg"}),
            _ev(2, "intro", {"player": "Neutrophil"}),
            _ev(3, "intro", {"player": "PulledTheBoys"}),  # this is the team name
        ]
        lines = self.reducer.reduce(events, snap)
        self.assertEqual(len(lines), 1)
        self.assertIn("Neutrophil", lines[0])
        self.assertIn("(PulledTheBoys)", lines[0])
        # Must NOT imply an upcoming opponent.
        self.assertNotIn("next", lines[0].lower())

    def test_burst_credits_winner_and_frames_score(self):
        # The exact bad-message burst (events 19-23).
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming", a_score=6, b_score=7)
        events = [
            _ev(1, "gg", {"kind": "gg"}),
            _ev(2, "intro", {"player": "Neutrophil"}),
            _ev(3, "intro", {"player": "PulledTheBoys"}),
            _ev(4, "score", {"team": "a", "from": 5, "to": 6}),
        ]
        lines = self.reducer.reduce(events, snap)
        # score line + player spotlight (plain gg is context, not its own line)
        self.assertEqual(len(lines), 2)
        joined = " || ".join(lines)
        self.assertIn("PulledTheBoys score is now 6", joined)
        self.assertIn("6 - 7", joined)
        self.assertIn("Neutrophil", joined)


class TestEventCoalescer(unittest.TestCase):
    def _coalescer(self):
        return EventCoalescer(quiet=20, max_window=60, winner_quiet=5, cooldown=30)

    def test_quiet_window_holds_then_flushes(self):
        c = self._coalescer()
        snap = _snapshot(a_score=9, b_score=6)
        c.add([_ev(1, "score", {"team": "a", "from": 8, "to": 9})], snap, now=0.0)
        # Within quiet window -> no flush
        self.assertIsNone(c.poll(now=5.0))
        # A second event resets the quiet timer
        c.add([_ev(2, "score", {"team": "a", "from": 9, "to": 10})], _snapshot(a_score=10, b_score=6), now=10.0)
        self.assertIsNone(c.poll(now=25.0))  # only 15s since last event
        # 20s of silence after last event -> flush, both events coalesced
        batch = c.poll(now=30.5)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.events), 2)
        self.assertTrue(batch.significant)
        self.assertEqual(len(batch.lines), 1)  # collapsed to one score line

    def test_cooldown_blocks_immediate_second_flush(self):
        c = self._coalescer()
        c.add([_ev(1, "intro", {"player": "A"})], _snapshot(), now=0.0)
        b1 = c.poll(now=21.0)
        self.assertIsNotNone(b1)
        # New event arrives during cooldown
        c.add([_ev(2, "intro", {"player": "B"})], _snapshot(), now=22.0)
        # Quiet window satisfied but cooldown (ends at 21+30=51) blocks it
        self.assertIsNone(c.poll(now=45.0))
        b2 = c.poll(now=52.0)
        self.assertIsNotNone(b2)

    def test_max_window_forces_flush_during_continuous_trickle(self):
        c = self._coalescer()
        snap = _snapshot()
        # An event every 10s never satisfies the 20s quiet window...
        for i in range(1, 8):
            c.add([_ev(i, "intro", {"player": f"P{i}"})], snap, now=float(i * 10))
            if i * 10 < 60:
                # before max window from first(=10): max fires at 10+60=70
                pass
        # At 71s, first_at was 10 -> 61s elapsed >= 60 max -> flush
        batch = c.poll(now=71.0)
        self.assertIsNotNone(batch)

    def test_winner_uses_shorter_window(self):
        c = self._coalescer()
        snap = _snapshot(a_score=11, b_score=6, series_winner="PulledTheBoys")
        c.add([_ev(1, "winner", {"team": "a", "name": "PulledTheBoys"})], snap, now=0.0)
        # Winner quiet window is 5s, not 20s
        self.assertIsNone(c.poll(now=3.0))
        batch = c.poll(now=6.0)
        self.assertIsNotNone(batch)

    def test_dedup_same_event_not_double_counted(self):
        c = self._coalescer()
        snap = _snapshot()
        e = _ev(1, "intro", {"player": "A"})
        self.assertEqual(c.add([e], snap, now=0.0), 1)
        self.assertEqual(c.add([e], snap, now=1.0), 0)  # same date+id -> ignored
        batch = c.poll(now=25.0)
        self.assertEqual(len(batch.events), 1)

    def test_no_pending_no_flush(self):
        c = self._coalescer()
        self.assertIsNone(c.poll(now=100.0))


class TestFeaturedMatchups(unittest.TestCase):
    def test_format_featured_matchups(self):
        cs = {"matches": [{"a": "Neutrophil", "b": "NukLeo", "scoreA": 3, "scoreB": 1}]}
        self.assertEqual(format_featured_matchups(cs), "Neutrophil 3-1 NukLeo")

    def test_format_empty(self):
        self.assertIsNone(format_featured_matchups(None))
        self.assertIsNone(format_featured_matchups({"matches": []}))

    def test_prompt_includes_scoreboard_context(self):
        snap = _snapshot()
        batch = FlushBatch([], snap, ["PulledTheBoys score is now 6 (PulledTheBoys 6 - 7 PSIOP Gaming)",
                                      "Player spotlight: Neutrophil (PulledTheBoys)"])
        _, user = build_summary_prompt(batch, scoreboard_context="Neutrophil 3-1 NukLeo")
        self.assertIn("Neutrophil 3-1 NukLeo", user)
        self.assertIn("if none name the spotlighted player", user.lower())


class TestScoreboardParsing(unittest.TestCase):
    CSV = (
        '"","","PulledTheBoys","",6,"","PSIOP Gaming","",7,"","",46110\n'
        '"","","","","","","","","","","map 1","map 2"\n'
        '"","1v1","(Z)MvonLipwig","",1,"","(P)Windshadow","",1,"","pylon","rainfall"\n'
        '"","1v1","(P)Neutrophil","",4,"","(Z) NuKLeO","",1,"","pylon","lightshade"\n'
        '"","2v2","(T)Dpoo","(P)LittleReaper","","","(Z)LanixMagi","(Z)JMPZ","","","TBD","TBD"\n'
    )

    def test_parse_teamleague_csv(self):
        from core.stream_production.scoreboard import parse_teamleague_csv
        d = parse_teamleague_csv(self.CSV)
        self.assertEqual(d["team_a"], "PulledTheBoys")
        self.assertEqual(d["score_a"], 6)
        self.assertEqual(d["team_b"], "PSIOP Gaming")
        self.assertEqual(d["score_b"], 7)
        # race prefixes stripped, matchups parsed
        m = {tuple(sorted([x.a, x.b])): x for x in d["matchups"]}
        neu = next(x for x in d["matchups"] if x.a == "Neutrophil")
        self.assertEqual(neu.b, "NuKLeO")
        self.assertEqual(neu.score_a, 4)
        self.assertEqual(neu.score_b, 1)
        self.assertEqual(neu.format(), "Neutrophil 4-1 NuKLeO")

    def test_2v2_row(self):
        from core.stream_production.scoreboard import parse_teamleague_csv
        d = parse_teamleague_csv(self.CSV)
        two = next(x for x in d["matchups"] if x.kind == "2v2")
        self.assertIn("Dpoo", two.a)
        self.assertIn("LittleReaper", two.a)

    def test_diff_detects_changed_row(self):
        from core.stream_production.scoreboard import parse_teamleague_csv, diff_matchups
        prev = parse_teamleague_csv(self.CSV)["matchups"]
        # Neutrophil goes 4 -> 5
        csv2 = self.CSV.replace('"(P)Neutrophil","",4,', '"(P)Neutrophil","",5,')
        curr = parse_teamleague_csv(csv2)["matchups"]
        changed = diff_matchups(prev, curr)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].a, "Neutrophil")
        self.assertEqual(changed[0].score_a, 5)

    def test_find_matchup_for_player_case_insensitive(self):
        from core.stream_production.scoreboard import parse_teamleague_csv, find_matchup_for_player
        ms = parse_teamleague_csv(self.CSV)["matchups"]
        m = find_matchup_for_player(ms, "nukleo")
        self.assertIsNotNone(m)
        self.assertEqual(m.a, "Neutrophil")

    def test_parse_custom_scoreboard(self):
        from core.stream_production.scoreboard import parse_custom_scoreboard
        d = parse_custom_scoreboard(
            {"matches": [{"a": "LittleReaper", "b": "ChienPwn", "scoreA": 3, "scoreB": 1}]}
        )
        self.assertEqual(len(d["matchups"]), 1)
        self.assertEqual(d["matchups"][0].format(), "LittleReaper 3-1 ChienPwn")

    def test_changed_with_winner_identifies_scorer(self):
        # The exact bug: NukLeo goes 1 -> 2; Neutrophil still leads 4-2.
        from core.stream_production.scoreboard import parse_teamleague_csv, changed_with_winner
        prev = parse_teamleague_csv(self.CSV)["matchups"]
        csv2 = self.CSV.replace('"(Z) NuKLeO","",1,', '"(Z) NuKLeO","",2,')
        curr = parse_teamleague_csv(csv2)["matchups"]
        cw = changed_with_winner(prev, curr)
        self.assertEqual(len(cw), 1)
        self.assertEqual(cw[0]["winner"], "NuKLeO")
        self.assertEqual(cw[0]["winner_score"], 2)
        self.assertEqual(cw[0]["loser"], "Neutrophil")
        self.assertEqual(cw[0]["loser_score"], 4)

    def test_describe_record_is_flip_proof(self):
        from core.stream_production.scoreboard import Matchup, describe_matchup_record
        m = Matchup("Neutrophil", 4, "NuKLeO", 2)
        s = describe_matchup_record(m, winner="NuKLeO", winner_score=2, loser="Neutrophil", loser_score=4)
        self.assertIn("NuKLeO: 2", s)
        self.assertIn("Neutrophil: 4", s)
        self.assertIn("Neutrophil leads", s)
        self.assertIn("won by NuKLeO", s)


class TestComposeStatement(unittest.TestCase):
    def test_game_win_head_to_head_not_flipped(self):
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming", a_score=6, b_score=8)
        events = [
            _ev(1, "gg", {"kind": "gg"}),
            _ev(2, "intro", {"player": "NukLeo"}),
            _ev(3, "intro", {"player": "PSIOP Gaming"}),
            _ev(4, "score", {"team": "b", "from": 7, "to": 8}),
        ]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        # NukLeo won this game but Neutrophil still leads the matchup 4-3.
        sb = {"a": "Neutrophil", "sa": 4, "b": "NukLeo", "sb": 3, "game_winner": "NukLeo"}
        msg = compose_statement(batch, sb)
        self.assertIn("NukLeo wins for PSIOP Gaming", msg)
        self.assertIn("Neutrophil leads the head-to-head 4-3", msg)
        self.assertNotIn("NukLeo leads", msg)

    def test_series_win_credits_deciding_player(self):
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming",
                         a_score=9, b_score=7, series_winner="PulledTheBoys")
        events = [
            _ev(1, "gg", {"kind": "match_gg"}),
            _ev(2, "intro", {"player": "Neutrophil"}),
            _ev(3, "intro", {"player": "PulledTheBoys"}),
            _ev(4, "score", {"team": "a", "from": 8, "to": 9}),
            _ev(5, "winner", {"team": "a", "name": "PulledTheBoys"}),
        ]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        sb = {"a": "Neutrophil", "sa": 5, "b": "NukLeo", "sb": 3, "game_winner": "Neutrophil"}
        msg = compose_statement(batch, sb)
        self.assertIn("Neutrophil takes the series for PulledTheBoys", msg)
        self.assertIn("Neutrophil leads the head-to-head 5-3", msg)

    def test_stale_series_winner_does_not_trigger_series(self):
        # A persistent series_winner from an earlier series must NOT label a later
        # game (no winner event in this batch) as a series win.
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming",
                         a_score=7, b_score=10, series_winner="PSIOP Gaming")
        events = [
            _ev(1, "gg", {"kind": "gg"}),
            _ev(2, "intro", {"player": "NukLeo"}),
            _ev(3, "intro", {"player": "PSIOP Gaming"}),
            _ev(4, "score", {"team": "b", "from": 9, "to": 10}),
        ]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        sb = {"a": "Neutrophil", "sa": 5, "b": "NukLeo", "sb": 4, "game_winner": "NukLeo"}
        msg = compose_statement(batch, sb)
        self.assertIn("NukLeo wins for PSIOP Gaming", msg)
        self.assertNotIn("series", msg.lower())

    def test_series_win_no_player_credit_on_team_mismatch(self):
        # Winner event says PSIOP, but the point just scored was for PulledTheBoys ->
        # don't credit the losing-side spotlight player; just state the team.
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming", a_score=7, b_score=9)
        events = [
            _ev(1, "gg", {"kind": "match_gg"}),
            _ev(2, "intro", {"player": "Neutrophil"}),
            _ev(3, "score", {"team": "a", "from": 6, "to": 7}),
            _ev(4, "winner", {"team": "b", "name": "PSIOP Gaming"}),
        ]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        sb = {"a": "Neutrophil", "sa": 5, "b": "NukLeo", "sb": 3, "game_winner": "Neutrophil"}
        msg = compose_statement(batch, sb)
        self.assertIn("PSIOP Gaming wins the series", msg)
        self.assertNotIn("takes the series", msg)

    def test_custom_game_uses_players_not_team_names(self):
        # Custom games come from the custom JSON (kind="custom"): two players, no teams.
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming", a_score=9, b_score=11)
        events = [
            _ev(1, "gg", {"kind": "gg"}),
            _ev(2, "intro", {"player": "LittleReaper"}),
            _ev(3, "score", {"team": "b", "from": 10, "to": 11}),
        ]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        sb = {"kind": "custom", "a": "LittleReaper", "sa": 3, "b": "ChienPwn",
              "sb": 2, "game_winner": "LittleReaper"}
        msg = compose_statement(batch, sb)
        self.assertIn("LittleReaper", msg)
        self.assertIn("ChienPwn", msg)
        self.assertNotIn("PulledTheBoys", msg)
        self.assertNotIn("PSIOP", msg)

    def test_game_win_without_score_event_omits_team_tally(self):
        # GG + intro but no team-league score event (typical of a custom game): never
        # leak the snapshot's stale team names/score.
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(a_name="PulledTheBoys", b_name="PSIOP Gaming", a_score=10, b_score=11)
        events = [_ev(1, "gg", {"kind": "gg"}), _ev(2, "intro", {"player": "LittleReaper"})]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        msg = compose_statement(batch, None)
        self.assertEqual(msg, "LittleReaper takes the game.")
        self.assertNotIn("PulledTheBoys", msg)

    def test_no_scene_chatter(self):
        # Scene-only burst -> nothing to say.
        from core.stream_production.coalescer import compose_statement
        snap = _snapshot(scene="scoreboard")
        events = [_ev(1, "scene", {"to": "scoreboard", "from": "sc2"})]
        batch = FlushBatch(events, snap, Reducer().reduce(events, snap))
        self.assertIsNone(compose_statement(batch, None))


class TestFlushBatch(unittest.TestCase):
    def test_is_batch_flag(self):
        snap = _snapshot()
        single = FlushBatch([], snap, ["Score update: A 1->2"])
        multi = FlushBatch([], snap, ["Score update: A 1->2", "Intro: B is up next"])
        self.assertFalse(single.is_batch)
        self.assertTrue(multi.is_batch)
        self.assertTrue(single.significant)


if __name__ == "__main__":
    unittest.main()
