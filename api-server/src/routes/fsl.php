<?php
/**
 * FSL read-only API (psistorm). Requires psistorm_db_config in config.php.
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

$fslUnavailable = function (Response $response) {
    $response->getBody()->write(json_encode([
        'error' => 'FSL unavailable',
        'message' => 'Configure psistorm_db_config in config.php (MySQL psistorm).',
    ]));
    return $response->withStatus(503)->withHeader('Content-Type', 'application/json');
};

// --- Players ---

// GET /api/v1/fsl/players/search?q=x&limit=40
$app->get('/api/v1/fsl/players/search', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $query = isset($q['q']) ? (string) $q['q'] : '';
        $limit = isset($q['limit']) ? (int) $q['limit'] : 40;
        $rows = $fslDb->searchPlayers($query, $limit);
        $response->getBody()->write(json_encode([
            'players' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/players/by-name?name=x
$app->get('/api/v1/fsl/players/by-name', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $name = isset($q['name']) ? trim((string) $q['name']) : '';
        if ($name === '') {
            $response->getBody()->write(json_encode(['error' => 'Bad Request', 'message' => 'Missing name']));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        $row = $fslDb->findPlayerByRealNameExact($name);
        if ($row === null) {
            $response->getBody()->write(json_encode(['player' => null]));
            return $response->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['player' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/players/{id}
$app->get('/api/v1/fsl/players/{id:[0-9]+}', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $row = $fslDb->getPlayerById((int) $args['id']);
        if ($row === null) {
            $response->getBody()->write(json_encode(['error' => 'Not Found', 'message' => 'Player not found']));
            return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['player' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Teams ---

$app->get('/api/v1/fsl/teams/search', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $query = isset($q['q']) ? (string) $q['q'] : '';
        $limit = isset($q['limit']) ? (int) $q['limit'] : 40;
        $rows = $fslDb->searchTeams($query, $limit);
        $response->getBody()->write(json_encode([
            'teams' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/teams/{team_id}/players — roster with Real_Name (captain/co/member)
$app->get('/api/v1/fsl/teams/{team_id:[0-9]+}/players', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $rows = $fslDb->listPlayersForTeam((int) $args['team_id']);
        $response->getBody()->write(json_encode([
            'players' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

$app->get('/api/v1/fsl/teams/{id:[0-9]+}', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $row = $fslDb->getTeamById((int) $args['id']);
        if ($row === null) {
            $response->getBody()->write(json_encode(['error' => 'Not Found', 'message' => 'Team not found']));
            return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['team' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Schedule ---

$app->get('/api/v1/fsl/schedule', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $season = isset($q['season']) ? $q['season'] : null;
        $week = isset($q['week']) ? $q['week'] : null;
        $limit = isset($q['limit']) ? (int) $q['limit'] : 120;
        $rows = $fslDb->listSchedule($season, $week, $limit);
        $response->getBody()->write(json_encode([
            'schedule' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// More specific route before /schedule/{id}
$app->get('/api/v1/fsl/schedule/{schedule_id:[0-9]+}/matches', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $rows = $fslDb->listScheduleMatchesForSchedule((int) $args['schedule_id']);
        $response->getBody()->write(json_encode([
            'links' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

$app->get('/api/v1/fsl/schedule/{schedule_id:[0-9]+}', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $row = $fslDb->getScheduleById((int) $args['schedule_id']);
        if ($row === null) {
            $response->getBody()->write(json_encode(['error' => 'Not Found', 'message' => 'Schedule row not found']));
            return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['entry' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Team league season summary (standings + finals-week winner proxy) ---
$app->get('/api/v1/fsl/team-league/season/{season:[0-9]+}/summary', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $summary = $fslDb->teamLeagueSeasonSummary((int) $args['season']);
        $response->getBody()->write(json_encode(['summary' => $summary]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Solo league division standings (fsl_matches.t_code S/A/B per season) ---
$app->get('/api/v1/fsl/solo-league/season/{season:[0-9]+}/division/{division:[sSaAbB]}/standings', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $season = (int) $args['season'];
        $division = strtoupper((string) $args['division']);
        $summary = $fslDb->soloDivisionSeasonStandings($season, $division);
        if (!empty($summary['error'])) {
            $response->getBody()->write(json_encode(['error' => 'Bad Request', 'message' => $summary['error']]));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['summary' => $summary]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Matches ---

$app->get('/api/v1/fsl/matches', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $season = isset($q['season']) ? $q['season'] : null;
        $playerName = isset($q['player_name']) ? (string) $q['player_name'] : null;
        $playerId = isset($q['player_id']) ? $q['player_id'] : null;
        $opponentName = isset($q['opponent_name']) ? (string) $q['opponent_name'] : null;
        $limit = isset($q['limit']) ? (int) $q['limit'] : 60;
        $rows = $fslDb->listMatches($season, $playerName, $playerId, $limit, $opponentName);
        $response->getBody()->write(json_encode([
            'matches' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/matches/h2h?player_name=&opponent_name= — full career (or season) H2H aggregates
$app->get('/api/v1/fsl/matches/h2h', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $a = isset($q['player_name']) ? (string) $q['player_name'] : '';
        $b = isset($q['opponent_name']) ? (string) $q['opponent_name'] : '';
        $season = isset($q['season']) && $q['season'] !== '' ? $q['season'] : null;
        if (trim($a) === '' || trim($b) === '') {
            $response->getBody()->write(json_encode(['error' => 'Bad Request', 'message' => 'player_name and opponent_name are required']));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        $row = $fslDb->aggregateHeadToHead($a, $b, $season);
        if ($row === null) {
            $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => 'H2H aggregate failed']));
            return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['h2h' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

$app->get('/api/v1/fsl/matches/{match_id:[0-9]+}', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $row = $fslDb->getMatchById((int) $args['match_id']);
        if ($row === null) {
            $response->getBody()->write(json_encode(['error' => 'Not Found', 'message' => 'Match not found']));
            return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode(['match' => $row]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// --- Statistics ---

// GET /api/v1/fsl/statistics/leaderboard/win-pct?min_matches=10&limit=15
$app->get('/api/v1/fsl/statistics/leaderboard/win-pct', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $minMatches = isset($q['min_matches']) ? (int) $q['min_matches'] : 10;
        $limit = isset($q['limit']) ? (int) $q['limit'] : 15;
        $rows = $fslDb->leaderboardMatchWinPct($minMatches, $limit);
        $response->getBody()->write(json_encode([
            'leaderboard' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/statistics/leaderboard/total-wins?min_matches=1&limit=15
$app->get('/api/v1/fsl/statistics/leaderboard/total-wins', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $minMatches = isset($q['min_matches']) ? (int) $q['min_matches'] : 1;
        $limit = isset($q['limit']) ? (int) $q['limit'] : 15;
        $rows = $fslDb->leaderboardMatchTotalWins($minMatches, $limit);
        $response->getBody()->write(json_encode([
            'leaderboard' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/fsl/statistics/leaderboard/maps-won?limit=15
$app->get('/api/v1/fsl/statistics/leaderboard/maps-won', function (Request $request, Response $response) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $q = $request->getQueryParams();
        $limit = isset($q['limit']) ? (int) $q['limit'] : 15;
        $rows = $fslDb->leaderboardStatisticsMapsWon($limit);
        $response->getBody()->write(json_encode([
            'leaderboard' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

$app->get('/api/v1/fsl/statistics/player/{player_id:[0-9]+}', function (Request $request, Response $response, array $args) use ($fslDb, $fslUnavailable) {
    if ($fslDb === null) {
        return $fslUnavailable($response);
    }
    try {
        $rows = $fslDb->listStatisticsForPlayer((int) $args['player_id']);
        $response->getBody()->write(json_encode([
            'statistics' => $rows,
            'count' => count($rows),
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode(['error' => 'Database Error', 'message' => $e->getMessage()]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});
