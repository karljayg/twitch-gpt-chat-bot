<?php
namespace Mathison\API\Middleware;

use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Http\Server\RequestHandlerInterface as RequestHandler;
use Slim\Psr7\Response;

class AuthMiddleware {
    private $api_key;
    
    public function __construct($api_key) {
        $this->api_key = $api_key;
    }
    
    public function __invoke(Request $request, RequestHandler $handler): Response {
        // Skip auth for health check
        $path = $request->getUri()->getPath();
        if ($path === '/health' || strpos($path, '/health') !== false) {
            return $handler->handle($request);
        }
        
        // Check Authorization header
        $auth_header = $request->getHeaderLine('Authorization');
        
        if (empty($auth_header)) {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Missing Authorization header. Use: Authorization: Bearer YOUR_API_KEY'
            ]));
            return $response
                ->withStatus(401)
                ->withHeader('Content-Type', 'application/json');
        }
        
        // Expected format: "Bearer YOUR_API_KEY"
        if ($auth_header !== "Bearer {$this->api_key}") {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Invalid API key'
            ]));
            return $response
                ->withStatus(401)
                ->withHeader('Content-Type', 'application/json');
        }
        
        // Continue to next middleware/route
        return $handler->handle($request);
    }
}

