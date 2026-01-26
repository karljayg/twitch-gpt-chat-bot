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

// GET /api/v1/replays/{replay_id}
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

