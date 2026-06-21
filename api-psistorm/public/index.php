<?php
/**
 * PsiStorm Database API - Generic Table Query System
 * Provides flexible REST API access to any table in the database
 */

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;
use PsiStorm\API\Database;
use PsiStorm\API\Middleware\AuthMiddleware;

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

// Set base path if configured
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

// Initialize database
try {
    $db = new Database(
        $db_config,
        $max_rows_per_query ?? 1000,
        $excluded_tables ?? []
    );
} catch (Exception $e) {
    http_response_code(500);
    die(json_encode([
        'error' => 'Database connection failed',
        'message' => $e->getMessage()
    ]));
}

// Add authentication middleware
$app->add(new AuthMiddleware($api_key));

// ===== ENDPOINTS =====

// Health check (no auth required)
$app->get('/health', function (Request $request, Response $response) use ($db) {
    $data = [
        'status' => 'healthy',
        'timestamp' => time(),
        'database' => $db->isConnected() ? 'connected' : 'disconnected',
        'api_version' => 'v1',
        'api_type' => 'generic'
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// Get all tables
$app->get('/api/v1/tables', function (Request $request, Response $response) use ($db) {
    try {
        $tables = $db->getTables();
        $response->getBody()->write(json_encode([
            'tables' => $tables,
            'count' => count($tables)
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// Get table schema
$app->get('/api/v1/tables/{table_name}/schema', function (Request $request, Response $response, array $args) use ($db) {
    try {
        $schema = $db->getTableSchema($args['table_name']);
        $response->getBody()->write(json_encode([
            'table' => $args['table_name'],
            'columns' => $schema
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// Get table row count
$app->get('/api/v1/tables/{table_name}/count', function (Request $request, Response $response, array $args) use ($db) {
    try {
        $count = $db->getTableRowCount($args['table_name']);
        $response->getBody()->write(json_encode([
            'table' => $args['table_name'],
            'count' => $count
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// SELECT from table
$app->post('/api/v1/tables/{table_name}/select', function (Request $request, Response $response, array $args) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        $columns = $body['columns'] ?? ['*'];
        $where = $body['where'] ?? [];
        $orderBy = $body['order_by'] ?? null;
        $limit = $body['limit'] ?? null;
        $offset = $body['offset'] ?? 0;
        
        $results = $db->select($args['table_name'], $columns, $where, $orderBy, $limit, $offset);
        
        $response->getBody()->write(json_encode([
            'table' => $args['table_name'],
            'rows' => $results,
            'count' => count($results)
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// INSERT into table
$app->post('/api/v1/tables/{table_name}/insert', function (Request $request, Response $response, array $args) use ($db, $read_only_mode) {
    if ($read_only_mode ?? false) {
        $response->getBody()->write(json_encode([
            'error' => 'Forbidden',
            'message' => 'API is in read-only mode'
        ]));
        return $response->withStatus(403)->withHeader('Content-Type', 'application/json');
    }
    
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['data'])) {
            $response->getBody()->write(json_encode([
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: data'
            ]));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->insert($args['table_name'], $body['data']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// UPDATE table
$app->put('/api/v1/tables/{table_name}/update', function (Request $request, Response $response, array $args) use ($db, $read_only_mode) {
    if ($read_only_mode ?? false) {
        $response->getBody()->write(json_encode([
            'error' => 'Forbidden',
            'message' => 'API is in read-only mode'
        ]));
        return $response->withStatus(403)->withHeader('Content-Type', 'application/json');
    }
    
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['data']) || empty($body['where'])) {
            $response->getBody()->write(json_encode([
                'error' => 'Bad Request',
                'message' => 'Missing required parameters: data and where'
            ]));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->update($args['table_name'], $body['data'], $body['where']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// DELETE from table
$app->delete('/api/v1/tables/{table_name}/delete', function (Request $request, Response $response, array $args) use ($db, $read_only_mode) {
    if ($read_only_mode ?? false) {
        $response->getBody()->write(json_encode([
            'error' => 'Forbidden',
            'message' => 'API is in read-only mode'
        ]));
        return $response->withStatus(403)->withHeader('Content-Type', 'application/json');
    }
    
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['where'])) {
            $response->getBody()->write(json_encode([
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: where (safety measure)'
            ]));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $result = $db->delete($args['table_name'], $body['where']);
        $response->getBody()->write(json_encode($result));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// Raw SQL query (SELECT only)
$app->post('/api/v1/query/raw', function (Request $request, Response $response) use ($db) {
    try {
        $body = json_decode($request->getBody()->getContents(), true);
        
        if (empty($body['sql'])) {
            $response->getBody()->write(json_encode([
                'error' => 'Bad Request',
                'message' => 'Missing required parameter: sql'
            ]));
            return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
        }
        
        $params = $body['params'] ?? [];
        $results = $db->rawQuery($body['sql'], $params);
        
        $response->getBody()->write(json_encode([
            'rows' => $results,
            'count' => count($results)
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    } catch (Exception $e) {
        $response->getBody()->write(json_encode([
            'error' => 'Database Error',
            'message' => $e->getMessage()
        ]));
        return $response->withStatus(500)->withHeader('Content-Type', 'application/json');
    }
});

// Run application
$app->run();
