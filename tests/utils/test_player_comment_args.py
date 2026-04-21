from utils.player_comment_args import split_replay_ref_prefix


def test_no_prefix_returns_full_body():
    ref, rest = split_replay_ref_prefix("ling bane all in")
    assert ref is None
    assert rest == "ling bane all in"


def test_positive_replay_id_prefix():
    ref, rest = split_replay_ref_prefix("25456 ling bane")
    assert ref == 25456
    assert rest == "ling bane"


def test_negative_games_ago_prefix():
    ref, rest = split_replay_ref_prefix("-3 roach macro")
    assert ref == -3
    assert rest == "roach macro"


def test_zero_not_treated_as_ref():
    ref, rest = split_replay_ref_prefix("0 gate expand")
    assert ref is None
    assert rest == "0 gate expand"
