<?php
/**
 * Replay-related endpoints
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

// GET /api/v1/replays/last
$app->get('/api/v1/replays/last', function (Request $request, Response $response) use ($db) {
    $result = $db->getLastReplayInfo();
    $response->getBody()->write(json_encode($result));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/replays/latest
$app->get('/api/v1/replays/latest', function (Request $request, Response $response) use ($db) {
    try {
        $result = $db->getLatestReplay();
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/replays/recency/{offset} — 0=latest, 1=one game ago (must be before /{replay_id})
$app->get('/api/v1/replays/recency/{offset}', function (Request $request, Response $response, array $args) use ($db) {
    try {
        $offset = isset($args['offset']) ? (int)$args['offset'] : 0;
        if ($offset < 0) {
            $data = ['error' => 'Bad Request', 'message' => 'offset must be >= 0'];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        $result = $db->getReplayByRecencyOffset($offset);
        if ($result === null) {
            $data = ['error' => 'Not Found', 'message' => 'No replay at that offset'];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
        }
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/replays/games?hours=X
$app->get('/api/v1/replays/games', function (Request $request, Response $response) use ($db) {
    try {
        $params = $request->getQueryParams();
        $hours = isset($params['hours']) ? (int)$params['hours'] : 24;
        
        $result = $db->getGamesForLastXHours($hours);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// PUT /api/v1/replays/last/comment - MUST come before parameterized routes
$app->put('/api/v1/replays/last/comment', function (Request $request, Response $response) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['comment'])) {
            $data = [
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: comment'
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->updatePlayerCommentsInLastReplay($body['comment']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// PUT /api/v1/replays/{replay_id}/comment - update specific replay comment
$app->put('/api/v1/replays/{replay_id}/comment', function (Request $request, Response $response, array $args) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        $replay_id = (int)($args['replay_id'] ?? 0);

        if ($replay_id <= 0 || empty($body['comment'])) {
            $data = [
                'error' => 'Bad Request',
                'message' => 'Missing required parameters: replay_id/comment'
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }

        $result = $db->updatePlayerCommentsByReplayId($replay_id, $body['comment']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// POST /api/v1/comments/save
$app->post('/api/v1/comments/save', function (Request $request, Response $response) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['comment_data'])) {
            $data = [
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: comment_data'
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->savePlayerCommentWithData($body['comment_data']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// POST /api/v1/patterns/save
$app->post('/api/v1/patterns/save', function (Request $request, Response $response) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['pattern_entry'])) {
            $data = [
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: pattern_entry'
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->savePatternToDb($body['pattern_entry']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// GET /api/v1/replays/{replay_id} - Parameterized route comes last
$app->get('/api/v1/replays/{replay_id}', function (Request $request, Response $response, array $args) use ($db) {
    $result = $db->getReplayById($args['replay_id']);
    
    if ($result === null) {
        $data = [
            'error' => 'Not Found',
            'message' => 'Replay not found'
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(404)->withHeader('Content-Type', 'application/json');
    }
    
    $response->getBody()->write(json_encode($result));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/build_orders/extract?opponent_name=X&opponent_race=Y&streamer_race=Z
$app->get('/api/v1/build_orders/extract', function (Request $request, Response $response) use ($db) {
    $params = $request->getQueryParams();
    
    $required = ['opponent_name', 'opponent_race', 'streamer_race'];
    foreach ($required as $param) {
        if (empty($params[$param])) {
            $data = [
                'error' => 'Bad Request',
                'message' => "Missing required parameter: {$param}"
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
    }
    
    $result = $db->extractOpponentBuildOrder(
        $params['opponent_name'],
        $params['opponent_race'],
        $params['streamer_race']
    );
    
    $response->getBody()->write(json_encode($result));
    return $response->withHeader('Content-Type', 'application/json');
});

// POST /api/v1/replays
$app->post('/api/v1/replays', function (Request $request, Response $response) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['replay_summary'])) {
            $data = [
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: replay_summary'
            ];
            $response->getBody()->write(json_encode($data));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->insertReplayInfo($body['replay_summary']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $data = [
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});


