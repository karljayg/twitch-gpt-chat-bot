<?php
/**
 * Mathison Database API - Entry Point
 * Using Slim Framework for routing and middleware
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;
use Mathison\API\Database;
use Mathison\API\FslDatabase;
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

$base_path = $base_path ?? '';
if ($base_path === '') {
    $scriptDir = str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME'] ?? ''));
    $uri = (string) parse_url('http://a' . ($_SERVER['REQUEST_URI'] ?? ''), PHP_URL_PATH);
    if ($scriptDir !== '' && $scriptDir !== '/' && stripos($uri, $scriptDir) === 0) {
        $base_path = $scriptDir;
    }
}
if ($base_path !== '') {
    $app->setBasePath(rtrim($base_path, '/'));
}

// Add routing middleware
$app->addRoutingMiddleware();

// Add error middleware
$errorMiddleware = $app->addErrorMiddleware(true, true, true);

// Initialize database (mathison)
try {
    $db = new Database($db_config);
} catch (Exception $e) {
    http_response_code(500);
    die(json_encode([
        'error' => 'Database connection failed',
        'message' => $e->getMessage()
    ]));
}

// Optional psistorm / FSL read-only API
$fslDb = null;
if (isset($psistorm_db_config) && is_array($psistorm_db_config) && !empty($psistorm_db_config['database'])) {
    try {
        $pc = $psistorm_db_config;
        if (empty($pc['charset'])) {
            $pc['charset'] = 'utf8mb4';
        }
        $fslDb = new FslDatabase($pc);
    } catch (\Throwable $e) {
        $fslDb = null;
    }
}

// Add authentication middleware (except /health)
$app->add(new AuthMiddleware($api_key));

// Health check endpoint (no auth required)
$app->get('/health', function (Request $request, Response $response) use ($db, $fslDb) {
    $fslStatus = 'disabled';
    if ($fslDb !== null) {
        $fslStatus = $fslDb->isConnected() ? 'connected' : 'disconnected';
    }
    $data = [
        'status' => 'healthy',
        'timestamp' => time(),
        'database' => $db->isConnected() ? 'connected' : 'disconnected',
        'fsl_database' => $fslStatus,
        'api_version' => 'v1'
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// Load route files
require __DIR__ . '/../src/routes/players.php';
require __DIR__ . '/../src/routes/replays.php';
require __DIR__ . '/../src/routes/fsl.php';

// Run application
$app->run();

