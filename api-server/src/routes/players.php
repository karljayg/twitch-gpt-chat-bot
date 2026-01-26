<?php
/**
 * Player-related endpoints
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

// GET /api/v1/players/check?player_name=X&player_race=Y
$app->get('/api/v1/players/check', function (Request $request, Response $response) use ($db) {
    $params = $request->getQueryParams();
    
    if (empty($params['player_name']) || empty($params['player_race'])) {
        $data = [
            'error' => 'Bad Request',
            'message' => 'Missing required parameters: player_name and player_race'
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
    }
    
    $result = $db->checkPlayerAndRaceExists($params['player_name'], $params['player_race']);
    $response->getBody()->write(json_encode($result));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/exists
$app->get('/api/v1/players/{player_name}/exists', function (Request $request, Response $response, array $args) use ($db) {
    $result = $db->checkPlayerExists($args['player_name']);
    $data = [
        'exists' => $result !== null,
        'data' => $result
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/records
$app->get('/api/v1/players/{player_name}/records', function (Request $request, Response $response, array $args) use ($db) {
    $records = $db->getPlayerRecords($args['player_name']);
    $response->getBody()->write(json_encode($records));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/comments?race=Protoss
$app->get('/api/v1/players/{player_name}/comments', function (Request $request, Response $response, array $args) use ($db) {
    $params = $request->getQueryParams();
    
    if (empty($params['race'])) {
        $data = [
            'error' => 'Bad Request',
            'message' => 'Missing required parameter: race'
        ];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
    }
    
    $comments = $db->getPlayerComments($args['player_name'], $params['race']);
    $response->getBody()->write(json_encode($comments));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/overall_records
$app->get('/api/v1/players/{player_name}/overall_records', function (Request $request, Response $response, array $args) use ($db) {
    $records = $db->getPlayerOverallRecords($args['player_name']);
    $response->getBody()->write(json_encode(['records' => $records]));
    return $response->withHeader('Content-Type', 'application/json');
});

