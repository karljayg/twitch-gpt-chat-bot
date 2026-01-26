<?php
/**
 * Mathison Database API - Entry Point
 * Using Slim Framework for routing and middleware
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;
use Mathison\API\Database;
use Mathison\API\Middleware\AuthMiddleware;

require __DIR__ . '/../vendor/autoload.php';

// Load configuration
$config_file = __DIR__ . '/../config.php';
if (!file_exists($config_file)) {
    http_response_code(500);
    die(json_encode([
        'error' => 'Configuration missing',
        'message' => 'Copy config.example.php to config.php and configure your database credentials'
    ]));
}
require $config_file;

// Create Slim app
$app = AppFactory::create();

// Add routing middleware
$app->addRoutingMiddleware();

// Add error middleware
$errorMiddleware = $app->addErrorMiddleware(true, true, true);

// Initialize database
try {
    $db = new Database($db_config);
} catch (Exception $e) {
    http_response_code(500);
    die(json_encode([
        'error' => 'Database connection failed',
        'message' => $e->getMessage()
    ]));
}

// Add authentication middleware (except /health)
$app->add(new AuthMiddleware($api_key));

// Health check endpoint (no auth required)
$app->get('/health', function (Request $request, Response $response) use ($db) {
    $data = [
        'status' => 'healthy',
        'timestamp' => time(),
        'database' => $db->isConnected() ? 'connected' : 'disconnected',
        'api_version' => 'v1'
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// Load route files
require __DIR__ . '/../src/routes/players.php';
require __DIR__ . '/../src/routes/replays.php';

// Run application
$app->run();

