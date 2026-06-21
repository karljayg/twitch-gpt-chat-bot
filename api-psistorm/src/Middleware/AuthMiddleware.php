<?php
namespace PsiStorm\API\Middleware;

use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Http\Server\RequestHandlerInterface as RequestHandler;
use Slim\Psr7\Response;

class AuthMiddleware {
    private $apiKey;
    
    public function __construct($apiKey) {
        $this->apiKey = $apiKey;
    }
    
    public function __invoke(Request $request, RequestHandler $handler): Response {
        // Skip auth for health endpoint
        $path = $request->getUri()->getPath();
        if (preg_match('#/health/?$#', $path)) {
            return $handler->handle($request);
        }
        
        // Check for Authorization header
        $authHeader = $request->getHeaderLine('Authorization');
        
        if (empty($authHeader)) {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Missing Authorization header'
            ]));
            return $response->withStatus(401)->withHeader('Content-Type', 'application/json');
        }
        
        // Verify Bearer token
        if (!preg_match('/Bearer\s+(.*)$/i', $authHeader, $matches)) {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Invalid Authorization header format. Use: Bearer YOUR_API_KEY'
            ]));
            return $response->withStatus(401)->withHeader('Content-Type', 'application/json');
        }
        
        $token = $matches[1];
        
        if ($token !== $this->apiKey) {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Invalid API key'
            ]));
            return $response->withStatus(401)->withHeader('Content-Type', 'application/json');
        }
        
        // Auth successful, continue to next middleware/route
        return $handler->handle($request);
    }
}
