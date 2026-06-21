-- =============================================================================
-- FSL MySQL (psistorm FSL DB) — run through your tunnel / mysql client.
-- Reusable test match: fsl_match_id = 99001 (config: FSL_TUNNEL_TEST_MATCH_ID).
-- API: player1 = winner = Freeedom (40), player2 = loser = SirMalagant (51).
-- =============================================================================

INSERT INTO fsl_matches (
    fsl_match_id,
    season,
    season_extra_info,
    notes,
    t_code,
    winner_player_id,
    winner_race,
    best_of,
    map_win,
    map_loss,
    loser_player_id,
    loser_race,
    winner_team_id,
    loser_team_id,
    source,
    vod
) VALUES (
    99001,
    99,
    NULL,
    'BOT_TUNNEL_TEST: Freeedom (W) vs SirMalagant — safe to spam votes',
    'S',
    40,
    'T',
    1,
    1,
    0,
    51,
    'P',
    NULL,
    NULL,
    NULL,
    NULL
)
ON DUPLICATE KEY UPDATE
    season = VALUES(season),
    season_extra_info = VALUES(season_extra_info),
    notes = VALUES(notes),
    t_code = VALUES(t_code),
    winner_player_id = VALUES(winner_player_id),
    winner_race = VALUES(winner_race),
    best_of = VALUES(best_of),
    map_win = VALUES(map_win),
    map_loss = VALUES(map_loss),
    loser_player_id = VALUES(loser_player_id),
    loser_race = VALUES(loser_race),
    winner_team_id = VALUES(winner_team_id),
    loser_team_id = VALUES(loser_team_id),
    source = VALUES(source),
    vod = VALUES(vod);

-- =============================================================================
-- 2026-04-11 Fix: chat votes used wrong reviewers.id (e.g. 1 = Nachoz, not TwitchChat).
-- Run as FSL MySQL admin. Then set FSL_BOT_REVIEWER_ID in settings/config.py to TwitchChat's id.
-- =============================================================================

-- Find reviewer ids (pick TwitchChat id for bot config):
-- SELECT id, name, weight, status FROM reviewers WHERE name IN ('TwitchChat', 'Nachoz');

-- Delete all votes for match 619 filed under reviewer NAME 'Nachoz' (mis-attributed bot batch).
-- If Nachoz had legitimate manual rows for this match, back them up first.
DELETE p FROM Player_Attribute_Votes p
INNER JOIN reviewers r ON p.reviewer_id = r.id
WHERE p.fsl_match_id = 619 AND r.name = 'Nachoz';

-- If you also mis-filed test match 99001 under Nachoz, uncomment:
-- DELETE p FROM Player_Attribute_Votes p
-- INNER JOIN reviewers r ON p.reviewer_id = r.id
-- WHERE p.fsl_match_id = 99001 AND r.name = 'Nachoz';

-- Rebuild aggregates after cleanup:
-- php aggregate_scores.php

-- 2026-04-21: api-server PHP only (deploy files; no DDL): routes
--   GET /api/v1/fsl/teams/{team_id}/players — roster via Players JOIN Teams;
--   GET /api/v1/fsl/statistics/leaderboard/total-wins — ORDER BY career series wins DESC.
--   GET /api/v1/fsl/statistics/leaderboard/maps-won — SUM(MapsW) after dedupe:
--     one row per (Player_ID, Division, Race) using MIN(Alias_ID) (same idea as player_statistics.php).
--   GET /api/v1/fsl/matches/h2h?player_name=&opponent_name=&season= — career/season H2H aggregates + Laplace next-series margins (PHP only; deploy FslDatabase + fsl.php).
--   GET /api/v1/fsl/team-league/season/{n}/summary — team league standings + winner of max week_number (no DDL).
