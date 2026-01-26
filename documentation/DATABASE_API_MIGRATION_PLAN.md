# Database API Migration Plan

## Overview

Transform Mathison's direct MySQL database access into a **Database API layer** that supports both:
1. **Local Mode**: Direct MySQL connection (current behavior)
2. **Remote Mode**: REST API calls to a separate database service

This enables:
- Database on a different server (scalability, security)
- Local development with simulated API (testing without remote dependencies)
- Clean separation of concerns (database logic isolated)

---

## Current Architecture

```
┌─────────────────┐
│   run_core.py   │
└────────┬────────┘
         │
         ├──> TwitchBot(db=Database())
         ├──> SqlReplayRepository(db)
         ├──> SqlPlayerRepository(db)
         ├──> AnalysisService(db)
         └──> OpponentAnalysisService(db)
                     │
                     ▼
            ┌────────────────┐
            │ mathison_db.py │
            │   Database()   │
            └───────┬────────┘
                    │
                    ▼
            ┌───────────────┐
            │  MySQL Server │
            │    (Local)    │
            └───────────────┘
```

### Current Database Usage Points

**Direct Database() instantiation:**
- `api/twitch_bot.py` (line 332)
- `utils/load_replays.py` (line 244)
- `load_learning_data.py` (line 80)
- Various debug scripts (8+ files)
- `api/discord_bot.py` (line 436)

**Through repositories:**
- `SqlReplayRepository` → wraps Database methods
- `SqlPlayerRepository` → wraps Database methods
- `AnalysisService` → direct Database access
- `OpponentAnalysisService` → direct Database access

---

## Proposed Architecture

```
┌─────────────────┐
│   run_core.py   │
└────────┬────────┘
         │
         ├──> TwitchBot(db_client)
         ├──> SqlReplayRepository(db_client)
         ├──> SqlPlayerRepository(db_client)
         ├──> AnalysisService(db_client)
         └──> OpponentAnalysisService(db_client)
                     │
                     ▼
         ┌───────────────────────┐
         │   IDatabaseClient     │  ◄── Interface
         │     (interface)       │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐    ┌──────────────────┐
│ LocalDatabase  │    │ ApiDatabaseClient│
│    Client      │    │                  │
└───────┬────────┘    └────────┬─────────┘
        │                      │
        ▼                      ▼
┌───────────────┐    ┌─────────────────┐
│  MySQL        │    │  REST API       │
│  (Direct)     │    │  (HTTP/HTTPS)   │
└───────────────┘    └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Database API   │
                     │    Service      │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  MySQL Server   │
                     │   (Remote)      │
                     └─────────────────┘
```

---

## Implementation Plan

### Phase 1: Create Database Interface & Clients

#### 1.1 Define IDatabaseClient Interface

**File**: `core/interfaces/i_database_client.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IDatabaseClient(ABC):
    """
    Interface for database operations.
    Implementations can use direct MySQL or REST API.
    """
    
    # Player Operations
    @abstractmethod
    def check_player_and_race_exists(self, player_name: str, player_race: str) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def check_player_exists(self, player_name: str) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_player_records(self, player_name: str) -> List[str]:
        pass
    
    @abstractmethod
    def get_player_comments(self, player_name: str, player_race: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_player_overall_records(self, player_name: str) -> str:
        pass
    
    # Replay Operations
    @abstractmethod
    def insert_replay_info(self, replay_info: Dict) -> int:
        pass
    
    @abstractmethod
    def get_last_replay_info(self) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def update_replay_comment(self, replay_id: int, comment: str) -> bool:
        pass
    
    @abstractmethod
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        pass
    
    # Build Order & Pattern Operations
    @abstractmethod
    def get_all_replays_with_comments(self) -> List[Dict]:
        pass
    
    # Connection Management
    @abstractmethod
    def ensure_connection(self):
        pass
    
    @abstractmethod
    def keep_connection_alive(self):
        pass
    
    # Legacy compatibility
    @property
    @abstractmethod
    def cursor(self):
        """For legacy code compatibility"""
        pass
    
    @property
    @abstractmethod
    def connection(self):
        """For legacy code compatibility"""
        pass
    
    @property
    @abstractmethod
    def logger(self):
        pass
```

#### 1.2 Create LocalDatabaseClient

**File**: `adapters/database/local_database_client.py`

```python
from core.interfaces.i_database_client import IDatabaseClient
from models.mathison_db import Database

class LocalDatabaseClient(IDatabaseClient):
    """
    Direct MySQL connection using the existing Database class.
    This is the current behavior wrapped in the new interface.
    """
    
    def __init__(self):
        self._db = Database()
    
    def check_player_and_race_exists(self, player_name: str, player_race: str):
        return self._db.check_player_and_race_exists(player_name, player_race)
    
    def check_player_exists(self, player_name: str):
        return self._db.check_player_exists(player_name)
    
    def get_player_records(self, player_name: str):
        return self._db.get_player_records(player_name)
    
    def get_player_comments(self, player_name: str, player_race: str):
        return self._db.get_player_comments(player_name, player_race)
    
    def get_player_overall_records(self, player_name: str):
        return self._db.get_player_overall_records(player_name)
    
    def insert_replay_info(self, replay_info: dict):
        return self._db.insert_replay_info(replay_info)
    
    def get_last_replay_info(self):
        return self._db.get_last_replay_info()
    
    def get_replay_by_id(self, replay_id: int):
        return self._db.get_replay_by_id(replay_id)
    
    def update_replay_comment(self, replay_id: int, comment: str):
        return self._db.update_replay_comment(replay_id, comment)
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str):
        return self._db.extract_opponent_build_order(opponent_name, opp_race, streamer_picked_race)
    
    def get_all_replays_with_comments(self):
        return self._db.get_all_replays_with_comments()
    
    def ensure_connection(self):
        return self._db.ensure_connection()
    
    def keep_connection_alive(self):
        return self._db.keep_connection_alive()
    
    @property
    def cursor(self):
        return self._db.cursor
    
    @property
    def connection(self):
        return self._db.connection
    
    @property
    def logger(self):
        return self._db.logger
```

#### 1.3 Create ApiDatabaseClient

**File**: `adapters/database/api_database_client.py`

```python
import requests
import logging
from typing import List, Dict, Any, Optional
from core.interfaces.i_database_client import IDatabaseClient
from settings import config

class ApiDatabaseClient(IDatabaseClient):
    """
    REST API client for remote database operations.
    Communicates with a separate database API service.
    """
    
    def __init__(self, api_base_url: str = None, api_key: str = None):
        self.api_base_url = api_base_url or config.DB_API_URL
        self.api_key = api_key or config.DB_API_KEY
        self.logger = logging.getLogger("ApiDatabaseClient")
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> Any:
        """Generic API request handler with error handling"""
        url = f"{self.api_base_url}{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url, params=data, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=10)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {method} {endpoint} - {e}")
            raise
    
    def check_player_and_race_exists(self, player_name: str, player_race: str):
        return self._make_request('GET', '/api/v1/players/check', {
            'player_name': player_name,
            'player_race': player_race
        })
    
    def check_player_exists(self, player_name: str):
        return self._make_request('GET', f'/api/v1/players/{player_name}/exists')
    
    def get_player_records(self, player_name: str):
        return self._make_request('GET', f'/api/v1/players/{player_name}/records')
    
    def get_player_comments(self, player_name: str, player_race: str):
        return self._make_request('GET', f'/api/v1/players/{player_name}/comments', {
            'race': player_race
        })
    
    def get_player_overall_records(self, player_name: str):
        return self._make_request('GET', f'/api/v1/players/{player_name}/overall_records')
    
    def insert_replay_info(self, replay_info: dict):
        result = self._make_request('POST', '/api/v1/replays', replay_info)
        return result.get('replay_id')
    
    def get_last_replay_info(self):
        return self._make_request('GET', '/api/v1/replays/last')
    
    def get_replay_by_id(self, replay_id: int):
        return self._make_request('GET', f'/api/v1/replays/{replay_id}')
    
    def update_replay_comment(self, replay_id: int, comment: str):
        result = self._make_request('PUT', f'/api/v1/replays/{replay_id}/comment', {
            'comment': comment
        })
        return result.get('success', False)
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str):
        return self._make_request('GET', '/api/v1/build_orders/extract', {
            'opponent_name': opponent_name,
            'opponent_race': opp_race,
            'streamer_race': streamer_picked_race
        })
    
    def get_all_replays_with_comments(self):
        return self._make_request('GET', '/api/v1/replays/with_comments')
    
    def ensure_connection(self):
        """API doesn't need explicit connection management"""
        return True
    
    def keep_connection_alive(self):
        """API doesn't need heartbeat"""
        pass
    
    @property
    def cursor(self):
        """Not applicable for API client - for legacy compatibility only"""
        raise NotImplementedError("API client doesn't use cursors")
    
    @property
    def connection(self):
        """Not applicable for API client - for legacy compatibility only"""
        raise NotImplementedError("API client doesn't use direct connections")
```

---

### Phase 2: Database API Service (PHP Implementation)

#### 2.1 Technology Decision: PHP

**Why PHP?**

The production webserver is already running PHP, which makes this the simplest choice:

- ✅ **No New Infrastructure**: Uses existing PHP webserver
- ✅ **Simple Deployment**: Copy `api-server/` folder to webroot, edit config, done
- ✅ **No Process Management**: No need for systemd, supervisor, or daemon management
- ✅ **Familiar Stack**: Leverages existing PHP knowledge and setup
- ✅ **Self-Contained**: All code in one folder, easy to maintain
- ✅ **Low Complexity**: No Python runtime, no reverse proxies, no port management
- ✅ **Easy Updates**: Copy new files, no service restarts needed (just PHP opcache)

**Deployment Simplicity:**
```bash
# On PHP server:
cd /var/www/html/
cp -r /path/to/repo/api-server mathison-api
cd mathison-api
cp config.example.php config.php
nano config.php  # Edit MySQL credentials and API key
# Done! API is live at https://yourdomain.com/mathison-api/
```

Compare to Python deployment:
- Need Python 3.8+, virtualenv, pip packages
- Need process manager (systemd/supervisor)
- Need reverse proxy configuration (nginx/apache)
- Need to manage daemon lifecycle
- More moving parts = more potential failures

**Principle: Keep It Simple**

The bot is Python, the API is PHP. Each runs in its natural environment:
- **Bot**: Python on desktop/local server (needs SC2 client access)
- **API**: PHP on web server (where MySQL already lives)

No need to run Python on the webserver or PHP on the bot machine.

#### 2.2 API Service Structure (Using Slim Framework)

**Folder**: `api-server/` (in main repo, self-contained)

We use **Slim Framework** - a lightweight, mature PHP microframework that provides routing, middleware, and error handling with minimal overhead.

**Why Slim?**
- Saves ~80% of custom routing/middleware code
- Battle-tested (10+ years, millions of downloads)
- Still self-contained (vendor/ folder travels with code)
- Simple deployment: `composer install`, done
- Better error handling and security out-of-the-box

```
twitch-gpt-chat-bot/
├── api-server/                  # Self-contained PHP API
│   ├── composer.json            # Dependencies (Slim + PDO)
│   ├── composer.lock            # Locked versions
│   ├── vendor/                  # Slim framework (auto-generated, gitignored)
│   ├── public/
│   │   └── index.php            # Entry point (~50 lines)
│   ├── src/
│   │   ├── Database.php         # MySQL connection & queries
│   │   ├── middleware/
│   │   │   └── AuthMiddleware.php  # API key validation
│   │   └── routes/
│   │       ├── players.php      # Player endpoints
│   │       ├── replays.php      # Replay endpoints
│   │       ├── build_orders.php # Build order endpoints
│   │       └── patterns.php     # Pattern endpoints (Phase 7)
│   ├── config.example.php       # Template (committed to git)
│   ├── config.php               # Actual config (gitignored)
│   ├── .htaccess                # URL rewriting to public/index.php
│   ├── README.md                # Deployment instructions
│   └── .gitignore               # Ignore config.php and vendor/
```

#### 2.3 Slim Framework Implementation

##### File: `api-server/composer.json`

```json
{
    "name": "mathison/database-api",
    "description": "REST API for Mathison database access",
    "type": "project",
    "require": {
        "php": ">=7.4",
        "slim/slim": "^4.12",
        "slim/psr7": "^1.6"
    },
    "autoload": {
        "psr-4": {
            "Mathison\\API\\": "src/"
        }
    }
}
```

##### File: `api-server/public/index.php`

```php
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
require __DIR__ . '/../config.php';

// Create Slim app
$app = AppFactory::create();
$app->addRoutingMiddleware();
$app->addErrorMiddleware(true, true, true);

// Initialize database
$db = new Database($db_config);

// Add authentication middleware (except /health)
$app->add(new AuthMiddleware($api_key));

// Health check (no auth required)
$app->get('/health', function (Request $request, Response $response) use ($db) {
    $data = [
        'status' => 'healthy',
        'timestamp' => time(),
        'database' => $db->isConnected() ? 'connected' : 'disconnected'
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// Load route files
require __DIR__ . '/../src/routes/players.php';
require __DIR__ . '/../src/routes/replays.php';
require __DIR__ . '/../src/routes/build_orders.php';

$app->run();
```

##### File: `api-server/src/middleware/AuthMiddleware.php`

```php
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
        if ($path === '/health') {
            return $handler->handle($request);
        }
        
        // Check Authorization header
        $auth_header = $request->getHeaderLine('Authorization');
        if ($auth_header !== "Bearer {$this->api_key}") {
            $response = new Response();
            $response->getBody()->write(json_encode([
                'error' => 'Unauthorized',
                'message' => 'Invalid or missing API key'
            ]));
            return $response
                ->withStatus(401)
                ->withHeader('Content-Type', 'application/json');
        }
        
        // Continue to next middleware/route
        return $handler->handle($request);
    }
}
```

##### File: `api-server/src/Database.php`

```php
<?php
namespace Mathison\API;

use PDO;
use PDOException;

class Database {
    private $conn;
    private $config;
    
    public function __construct($config) {
        $this->config = $config;
        $this->connect();
    }
    
    private function connect() {
        $dsn = "mysql:host={$this->config['host']};dbname={$this->config['database']};charset={$this->config['charset']}";
        
        try {
            $this->conn = new PDO($dsn, $this->config['user'], $this->config['password'], [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false
            ]);
        } catch (PDOException $e) {
            throw new \Exception("Database connection failed: " . $e->getMessage());
        }
    }
    
    public function isConnected() {
        return $this->conn !== null;
    }
    
    public function checkPlayerAndRaceExists($player_name, $player_race) {
        $sql = "
            SELECT r.*, 
                   p1.SC2_UserId AS Player1_Name,
                   p2.SC2_UserId AS Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE ((p1.SC2_UserId = ? AND r.Player1_Race = ?)
                OR (p2.SC2_UserId = ? AND r.Player2_Race = ?))
            ORDER BY r.Date_Played DESC
            LIMIT 1
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name, $player_race, $player_name, $player_race]);
        return $stmt->fetch();
    }
    
    public function checkPlayerExists($player_name) {
        $sql = "SELECT * FROM Players WHERE SC2_UserId = ? LIMIT 1";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name]);
        return $stmt->fetch();
    }
    
    public function getPlayerRecords($player_name) {
        $sql = "
            SELECT 
                CONCAT(p1.SC2_UserId, ', ', p2.SC2_UserId, ', ',
                       COALESCE(SUM(CASE WHEN r.Player1_Result = 'Win' THEN 1 ELSE 0 END), 0), ' wins, ',
                       COALESCE(SUM(CASE WHEN r.Player1_Result = 'Lose' THEN 1 ELSE 0 END), 0), ' losses') as record
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE p1.SC2_UserId = ?
            GROUP BY p1.SC2_UserId, p2.SC2_UserId
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name]);
        return $stmt->fetchAll(PDO::FETCH_COLUMN);
    }
    
    public function getPlayerComments($player_name, $player_race) {
        $sql = "
            SELECT 
                r.Player_Comments,
                r.Map,
                r.Date_Played,
                r.GameDuration
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE ((p1.SC2_UserId = ? AND r.Player1_Race = ?)
                OR (p2.SC2_UserId = ? AND r.Player2_Race = ?))
                AND r.Player_Comments IS NOT NULL
                AND r.GameDuration > '00:02:00'
            ORDER BY r.Date_Played DESC
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name, $player_race, $player_name, $player_race]);
        
        $results = [];
        foreach ($stmt->fetchAll() as $row) {
            $results[] = [
                'player_comments' => $row['Player_Comments'],
                'map' => $row['Map'],
                'date_played' => $row['Date_Played'],
                'game_duration' => $row['GameDuration']
            ];
        }
        return $results;
    }
    
    // Additional methods...
}
```

##### File: `api-server/src/routes/players.php`

```php
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
        $data = ['error' => 'Missing player_name or player_race parameter'];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
    }
    
    $result = $db->checkPlayerAndRaceExists($params['player_name'], $params['player_race']);
    $response->getBody()->write(json_encode($result));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/exists
$app->get('/api/v1/players/{player_name}/exists', function (Request $request, Response $response, $args) use ($db) {
    $result = $db->checkPlayerExists($args['player_name']);
    $data = [
        'exists' => $result !== false,
        'data' => $result
    ];
    $response->getBody()->write(json_encode($data));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/records
$app->get('/api/v1/players/{player_name}/records', function (Request $request, Response $response, $args) use ($db) {
    $records = $db->getPlayerRecords($args['player_name']);
    $response->getBody()->write(json_encode($records));
    return $response->withHeader('Content-Type', 'application/json');
});

// GET /api/v1/players/{player_name}/comments?race=Protoss
$app->get('/api/v1/players/{player_name}/comments', function (Request $request, Response $response, $args) use ($db) {
    $params = $request->getQueryParams();
    
    if (empty($params['race'])) {
        $data = ['error' => 'Missing race parameter'];
        $response->getBody()->write(json_encode($data));
        return $response->withStatus(400)->withHeader('Content-Type', 'application/json');
    }
    
    $comments = $db->getPlayerComments($args['player_name'], $params['race']);
    $response->getBody()->write(json_encode($comments));
    return $response->withHeader('Content-Type', 'application/json');
});
```

##### File: `api-server/config.example.php`

```php
<?php
/**
 * Database API Configuration Template
 * 
 * Copy this file to config.php and fill in your values
 * config.php is gitignored for security
 */

// MySQL Database Configuration
$db_config = [
    'host'     => 'localhost',
    'user'     => 'your_mysql_user',
    'password' => 'your_mysql_password',
    'database' => 'mathison',
    'charset'  => 'utf8mb4'
];

// API Security
$api_key = 'your-secure-api-key-here-change-this';
```

**File**: `api-server/.htaccess`

```apache
# Redirect all requests to public/index.php (Slim Framework)
<IfModule mod_rewrite.c>
    RewriteEngine On
    
    # Redirect to public/ folder
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ public/index.php [QSA,L]
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options "nosniff"
    Header set X-Frame-Options "DENY"
    Header set X-XSS-Protection "1; mode=block"
</IfModule>
```

**File**: `api-server/.gitignore`

```gitignore
# Configuration (contains credentials)
config.php

# Composer dependencies
/vendor/

# IDE files
.vscode/
.idea/

# Logs (if any)
*.log
```

**File**: `api-server/README.md`

```markdown
# Mathison Database API

REST API for remote Mathison database access using Slim Framework.

## Installation

### 1. Copy to Server

```bash
# On your PHP server
cd /var/www/html/
cp -r /path/to/repo/api-server mathison-api
cd mathison-api
```

### 2. Install Dependencies

```bash
# Install Slim Framework via Composer
composer install --no-dev --optimize-autoloader
```

**Note**: If composer is not installed:
```bash
# Install composer first
curl -sS https://getcomposer.org/installer | php
php composer.phar install --no-dev --optimize-autoloader
```

### 3. Configure

```bash
# Copy configuration template
cp config.example.php config.php

# Edit with your MySQL credentials
nano config.php
```

Set your MySQL credentials and generate a secure API key:
```php
$db_config = [
    'host'     => 'localhost',
    'user'     => 'your_user',
    'password' => 'your_password',
    'database' => 'mathison',
    'charset'  => 'utf8mb4'
];

$api_key = 'generate-a-secure-random-key-here';
```

### 4. Set Permissions

```bash
# Ensure Apache can read files
chmod -R 755 .
chmod 644 config.php  # Protect config file
```

### 5. Test

```bash
# Health check (no auth required)
curl https://yourdomain.com/mathison-api/health

# Test authenticated endpoint
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://yourdomain.com/mathison-api/api/v1/players/check?player_name=TestPlayer&player_race=Protoss"
```

## API Endpoints

### Health Check
- `GET /health` - No authentication required
- Returns: `{"status": "healthy", "timestamp": 1234567890, "database": "connected"}`

### Players
- `GET /api/v1/players/check?player_name=X&player_race=Y`
- `GET /api/v1/players/{player_name}/exists`
- `GET /api/v1/players/{player_name}/records`
- `GET /api/v1/players/{player_name}/comments?race=Protoss`

### Replays
- `GET /api/v1/replays/last`
- `GET /api/v1/replays/{replay_id}`
- `POST /api/v1/replays` - Create new replay
- `PUT /api/v1/replays/{replay_id}/comment` - Update comment

### Build Orders
- `GET /api/v1/build_orders/extract?opponent_name=X&opponent_race=Y&streamer_race=Z`

## Authentication

All endpoints (except `/health`) require an API key in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY_HERE
```

## Updating

```bash
cd /var/www/html/mathison-api
git pull  # If using git
composer install --no-dev --optimize-autoloader
# No service restart needed - PHP automatically uses new code
```

## Troubleshooting

### Error: "Class not found"
```bash
# Regenerate autoloader
composer dump-autoload
```

### Error: "Database connection failed"
- Check `config.php` credentials
- Verify MySQL is running: `systemctl status mysql`
- Test connection: `mysql -u USERNAME -p`

### Error: "Unauthorized"
- Check API key in bot's `config.py` matches `api-server/config.php`
- Ensure Authorization header format: `Bearer YOUR_KEY`

### Error: 404 on all endpoints
- Check `.htaccess` is being read: `sudo a2enmod rewrite && sudo systemctl restart apache2`
- Verify AllowOverride is enabled in Apache config

## Development

Run locally for testing:
```bash
cd api-server
php -S localhost:8000 -t public
```

Then test at: `http://localhost:8000/health`
```

#### 2.4 API Extensibility & Future-Proofing

**Design Principles for Long-Term Maintainability:**

##### A) Version the API

Use versioned endpoints to allow changes without breaking existing clients:

```
/api/v1/players/...    # Current version
/api/v2/players/...    # Future version with breaking changes
```

**In code:**
```php
// api-server/lib/Router.php
public function handleRequest() {
    // Extract API version from path
    if (preg_match('#^api/(v\d+)/(.+)#', $path, $matches)) {
        $version = $matches[1];  // 'v1', 'v2', etc.
        $endpoint = $matches[2];
        
        // Route to version-specific handler
        if ($version === 'v1') {
            $this->handleV1($endpoint);
        } elseif ($version === 'v2') {
            $this->handleV2($endpoint);
        }
    }
}
```

**Benefits:**
- Can add new fields to v2 without breaking v1 clients
- Can restructure responses in v2
- Old bot installations keep working on v1

##### B) Schema Versioning

Track database schema version to handle migrations:

```sql
-- Add to your MySQL database
CREATE TABLE IF NOT EXISTS Schema_Version (
    Version INT PRIMARY KEY,
    Applied_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Description VARCHAR(255)
);

INSERT INTO Schema_Version (Version, Description) 
VALUES (1, 'Initial schema');
```

**In API:**
```php
// api-server/lib/Database.php
public function getSchemaVersion() {
    $sql = "SELECT MAX(Version) as version FROM Schema_Version";
    $result = $this->conn->query($sql)->fetch();
    return $result['version'] ?? 0;
}

// Health check includes schema version
// GET /health returns:
// {"status": "healthy", "schema_version": 1, "api_version": "v1"}
```

##### C) Generic Query Builder (for flexibility)

Add a flexible query method for future tables:

```php
// api-server/lib/Database.php
/**
 * Generic SELECT query builder
 * Allows querying any table without hardcoding methods
 */
public function select($table, $where = [], $columns = '*', $orderBy = null, $limit = null) {
    // Whitelist allowed tables for security
    $allowed_tables = ['Players', 'Replays', 'Patterns', 'Player_Comments'];
    if (!in_array($table, $allowed_tables)) {
        throw new Exception("Table not allowed: $table");
    }
    
    $sql = "SELECT $columns FROM $table";
    $params = [];
    
    if (!empty($where)) {
        $conditions = [];
        foreach ($where as $col => $val) {
            $conditions[] = "$col = ?";
            $params[] = $val;
        }
        $sql .= " WHERE " . implode(' AND ', $conditions);
    }
    
    if ($orderBy) {
        $sql .= " ORDER BY $orderBy";
    }
    
    if ($limit) {
        $sql .= " LIMIT " . (int)$limit;
    }
    
    $stmt = $this->conn->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetchAll();
}

/**
 * Generic INSERT
 */
public function insert($table, $data) {
    $allowed_tables = ['Players', 'Replays', 'Patterns', 'Player_Comments'];
    if (!in_array($table, $allowed_tables)) {
        throw new Exception("Table not allowed: $table");
    }
    
    $columns = implode(', ', array_keys($data));
    $placeholders = implode(', ', array_fill(0, count($data), '?'));
    
    $sql = "INSERT INTO $table ($columns) VALUES ($placeholders)";
    $stmt = $this->conn->prepare($sql);
    $stmt->execute(array_values($data));
    
    return $this->conn->lastInsertId();
}

/**
 * Generic UPDATE
 */
public function update($table, $data, $where) {
    $allowed_tables = ['Players', 'Replays', 'Patterns', 'Player_Comments'];
    if (!in_array($table, $allowed_tables)) {
        throw new Exception("Table not allowed: $table");
    }
    
    $set = [];
    $params = [];
    foreach ($data as $col => $val) {
        $set[] = "$col = ?";
        $params[] = $val;
    }
    
    $conditions = [];
    foreach ($where as $col => $val) {
        $conditions[] = "$col = ?";
        $params[] = $val;
    }
    
    $sql = "UPDATE $table SET " . implode(', ', $set) . 
           " WHERE " . implode(' AND ', $conditions);
    
    $stmt = $this->conn->prepare($sql);
    return $stmt->execute($params);
}
```

**Usage:**
```php
// Future: Add new table without changing Database.php
$results = $db->select('New_Table', ['field' => 'value']);

// Insert into new table
$id = $db->insert('New_Table', [
    'field1' => 'value1',
    'field2' => 'value2'
]);
```

##### D) Dynamic Field Support

Handle new fields without code changes:

```php
// api-server/lib/Database.php
/**
 * Get all columns for a table dynamically
 */
public function getTableColumns($table) {
    $sql = "SHOW COLUMNS FROM $table";
    $stmt = $this->conn->query($sql);
    return $stmt->fetchAll(PDO::FETCH_COLUMN);
}

/**
 * Build SELECT with all available columns
 */
public function getPlayerFull($player_name) {
    $columns = $this->getTableColumns('Players');
    $columnList = implode(', ', $columns);
    
    $sql = "SELECT $columnList FROM Players WHERE SC2_UserId = ?";
    $stmt = $this->conn->prepare($sql);
    $stmt->execute([$player_name]);
    return $stmt->fetch();
}
```

**Benefits:**
- Add new columns to database, API automatically includes them
- No code changes needed for new fields
- Response automatically has new data

##### E) Configuration-Driven Endpoints

Define available operations in config:

```php
// api-server/config.php
$api_config = [
    'allowed_tables' => [
        'Players' => [
            'select' => true,
            'insert' => true,
            'update' => true,
            'delete' => false  // Don't allow player deletion via API
        ],
        'Replays' => [
            'select' => true,
            'insert' => true,
            'update' => true,
            'delete' => false
        ],
        'Patterns' => [
            'select' => true,
            'insert' => true,
            'update' => true,
            'delete' => true   // Allow pattern management
        ]
    ],
    
    'rate_limits' => [
        'default' => 100,  // requests per minute
        'write' => 20      // write operations per minute
    ]
];
```

##### F) Migration System

Handle schema changes over time:

```php
// api-server/migrations/001_add_player_rating.php
<?php
return [
    'version' => 2,
    'description' => 'Add rating field to Players table',
    'up' => "ALTER TABLE Players ADD COLUMN Rating INT DEFAULT 0",
    'down' => "ALTER TABLE Players DROP COLUMN Rating"
];
?>

// api-server/lib/Migrator.php
<?php
class Migrator {
    private $db;
    
    public function __construct($db) {
        $this->db = $db;
    }
    
    public function migrate() {
        $current_version = $this->db->getSchemaVersion();
        $migrations = $this->loadMigrations();
        
        foreach ($migrations as $migration) {
            if ($migration['version'] > $current_version) {
                echo "Applying migration {$migration['version']}: {$migration['description']}\n";
                $this->db->conn->exec($migration['up']);
                
                $sql = "INSERT INTO Schema_Version (Version, Description) VALUES (?, ?)";
                $stmt = $this->db->conn->prepare($sql);
                $stmt->execute([$migration['version'], $migration['description']]);
            }
        }
    }
    
    private function loadMigrations() {
        $files = glob(__DIR__ . '/../migrations/*.php');
        $migrations = [];
        
        foreach ($files as $file) {
            $migrations[] = require $file;
        }
        
        usort($migrations, fn($a, $b) => $a['version'] <=> $b['version']);
        return $migrations;
    }
}
?>

// Usage: Run migrations
// php api-server/migrate.php
```

##### G) OpenAPI/Swagger Documentation

Auto-generate API docs that update with changes:

```php
// api-server/docs.php
<?php
/**
 * Auto-generate OpenAPI documentation
 */
require_once 'config.php';
require_once 'lib/Database.php';

$db = new Database($db_config);

$spec = [
    'openapi' => '3.0.0',
    'info' => [
        'title' => 'Mathison Database API',
        'version' => '1.0.0'
    ],
    'paths' => []
];

// Auto-discover endpoints from allowed tables
foreach ($api_config['allowed_tables'] as $table => $operations) {
    if ($operations['select']) {
        $spec['paths']["/api/v1/$table"] = [
            'get' => [
                'summary' => "Get all $table",
                'responses' => [
                    '200' => ['description' => 'Success']
                ]
            ]
        ];
    }
    // ... generate other operations
}

header('Content-Type: application/json');
echo json_encode($spec, JSON_PRETTY_PRINT);
?>
```

**Access at:** `https://yourdomain.com/mathison-api/docs.php`

##### H) Backward Compatibility Strategy

When adding new features:

```php
// api-server/lib/Response.php
class Response {
    /**
     * Send JSON response with version-aware formatting
     */
    public static function success($data, $api_version = 'v1') {
        $response = [
            'success' => true,
            'data' => $data
        ];
        
        // v2 might add metadata
        if ($api_version === 'v2') {
            $response['meta'] = [
                'timestamp' => time(),
                'version' => 'v2'
            ];
        }
        
        http_response_code(200);
        echo json_encode($response);
        exit;
    }
}
```

### Extensibility Summary

With these patterns, you can:

| Change Type | How to Handle | Code Changes Needed |
|-------------|--------------|---------------------|
| **New Table** | Add to `allowed_tables` config | Config only |
| **New Field** | Add column to MySQL | None (auto-detected) |
| **New Endpoint** | Add route in `routes/` folder | New file |
| **Breaking Change** | Create v2 API endpoints | New version folder |
| **Schema Migration** | Add migration file | One PHP file |
| **New Query Type** | Use generic `select()`/`insert()` | None |

**Key Principle:** The API grows with your database schema, not the other way around.

**Example Growth Path:**
```
Phase 1: Basic CRUD on Players/Replays ✓
Phase 2: Add Patterns table → Just update config ✓
Phase 3: Add Rating field → ALTER TABLE, no API changes ✓
Phase 4: New analysis endpoints → Add routes/analysis.php ✓
Phase 5: Breaking changes → Create /api/v2/ ✓
```

The API is designed to be **data-driven** rather than **code-driven**, making it flexible for future needs.

---

### Phase 3: Configuration Changes

**File**: `settings/config.example.py`

Add new settings:

```python
"""
||   Database Settings
"""
# Database mode: 'local' or 'api'
DB_MODE = "local"  # Options: 'local', 'api'

# Local MySQL Settings (used when DB_MODE='local')
DB_HOST = "localhost"
DB_USER = ""
DB_PASSWORD = ""
DB_NAME = "mathison"
HEARTBEAT_MYSQL = 20

# API Database Settings (used when DB_MODE='api')
DB_API_URL = "http://localhost:8000"  # URL of the database API service
DB_API_KEY = "your-secure-api-key-here"  # API key for authentication

# For local development with simulated API:
# 1. Set DB_MODE = "api"
# 2. Set DB_API_URL = "http://localhost:8000"
# 3. Run: python -m uvicorn mathison_db_api.main:app --reload
```

---

### Phase 4: Factory Pattern for Client Creation

**File**: `adapters/database/database_client_factory.py`

```python
from core.interfaces.i_database_client import IDatabaseClient
from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from settings import config
import logging

logger = logging.getLogger("DatabaseClientFactory")

def create_database_client() -> IDatabaseClient:
    """
    Factory function to create the appropriate database client
    based on configuration.
    
    Returns:
        IDatabaseClient: Either LocalDatabaseClient or ApiDatabaseClient
    """
    db_mode = config.DB_MODE.lower()
    
    if db_mode == "local":
        logger.info("Creating LocalDatabaseClient (direct MySQL connection)")
        return LocalDatabaseClient()
    
    elif db_mode == "api":
        logger.info(f"Creating ApiDatabaseClient (API URL: {config.DB_API_URL})")
        return ApiDatabaseClient(
            api_base_url=config.DB_API_URL,
            api_key=config.DB_API_KEY
        )
    
    else:
        raise ValueError(f"Invalid DB_MODE: {db_mode}. Must be 'local' or 'api'")
```

---

### Phase 5: Update Application Code

#### 5.1 Update run_core.py

```python
# Old:
from api.twitch_bot import TwitchBot
twitch_bot_legacy = TwitchBot(start_monitor=False)
replay_repo = SqlReplayRepository(twitch_bot_legacy.db)

# New:
from adapters.database.database_client_factory import create_database_client
db_client = create_database_client()

from api.twitch_bot import TwitchBot
twitch_bot_legacy = TwitchBot(start_monitor=False, db_client=db_client)
replay_repo = SqlReplayRepository(db_client)
```

#### 5.2 Update TwitchBot

```python
# api/twitch_bot.py

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, start_monitor=True, db_client=None):
        # ... existing init code ...
        
        # Old:
        # self.db = Database()
        
        # New:
        if db_client is None:
            from adapters.database.database_client_factory import create_database_client
            self.db = create_database_client()
        else:
            self.db = db_client
```

#### 5.3 Update Repositories

```python
# core/repositories/sql_replay_repository.py

class SqlReplayRepository(IReplayRepository):
    def __init__(self, db_client: IDatabaseClient):
        self.db = db_client  # Now accepts interface instead of concrete Database
```

---

### Phase 6: Testing Strategy

#### 6.1 Unit Tests

```python
# tests/adapters/test_database_clients.py

import pytest
from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from unittest.mock import Mock, patch

def test_local_client_implements_interface():
    client = LocalDatabaseClient()
    assert hasattr(client, 'check_player_and_race_exists')
    assert hasattr(client, 'insert_replay_info')

@patch('adapters.database.api_database_client.requests.Session')
def test_api_client_makes_request(mock_session):
    mock_response = Mock()
    mock_response.json.return_value = {'exists': True}
    mock_session.return_value.get.return_value = mock_response
    
    client = ApiDatabaseClient(
        api_base_url="http://test",
        api_key="test_key"
    )
    result = client.check_player_exists("TestPlayer")
    
    assert result['exists'] == True
```

#### 6.2 Integration Tests

Test with both modes:
- Local mode against test database
- API mode against running test API service

---

## Migration Steps (Rollout Plan)

### Step 1: Preparation (No breaking changes)
1. Create `core/interfaces/i_database_client.py`
2. Create `adapters/database/local_database_client.py`
3. Create `adapters/database/database_client_factory.py`
4. Add config options (default to `DB_MODE="local"`)
5. Test that LocalDatabaseClient works identically to Database

### Step 2: Update Application (Backward compatible)
1. Update `run_core.py` to use factory
2. Update `TwitchBot.__init__()` to accept optional `db_client`
3. Update repositories to accept `IDatabaseClient`
4. Run full test suite - should work identically

### Step 3: Build Database API Service
1. Create separate `mathison-db-api` project
2. Copy `mathison_db.py` to API service
3. Implement FastAPI endpoints
4. Add authentication middleware
5. Deploy to test environment

### Step 4: Create ApiDatabaseClient
1. Implement `ApiDatabaseClient` class
2. Test against running API service
3. Verify all methods work correctly

### Step 5: Production Deployment
1. Deploy database API service to production
2. Update config on bot server: `DB_MODE="api"`
3. Monitor logs for any issues
4. Keep fallback to local mode if needed

---

## Local Development Workflow

### Option A: Full Local Stack (Current)
```bash
# config.py
DB_MODE = "local"
DB_HOST = "localhost"

# Run bot
python run_core.py
```

### Option B: Simulated API (Test API integration)
```bash
# Terminal 1: Run local API service
cd mathison-db-api
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Run bot with API mode
# config.py
DB_MODE = "api"
DB_API_URL = "http://localhost:8000"
DB_API_KEY = "dev-key-123"

python run_core.py
```

### Option C: Remote API (Production-like)
```bash
# config.py
DB_MODE = "api"
DB_API_URL = "https://api.mathison.psistorm.com"
DB_API_KEY = "prod-key-xyz"

python run_core.py
```

---

## Benefits

### Security
- Database credentials only on API server
- API key authentication
- No direct database exposure to bot server

### Scalability
- Database can be on powerful dedicated server
- Multiple bot instances can share same API
- Easier to scale database independently

### Maintainability
- Clean separation of concerns
- Easier to test (mock API client)
- Database logic centralized in one service

### Flexibility
- Switch between local/remote without code changes
- Local development without remote dependencies
- Can run database on different cloud provider

---

## Estimated Effort

- **Phase 1-2**: 8-12 hours (Interface, Local/API clients)
- **Phase 3**: 2 hours (Config changes)
- **Phase 4**: 1 hour (Factory pattern)
- **Phase 5**: 4-6 hours (Update application code)
- **Phase 6**: 4-6 hours (Testing)
- **Database API Service**: 12-16 hours (Separate project)

**Total**: ~30-40 hours

---

## Next Steps

1. Review and approve this plan
2. Create feature branch: `feature/database-api-migration`
3. Start with Phase 1 (non-breaking interface/local client)
4. Incremental testing at each phase
5. Deploy API service to staging
6. Production rollout with monitoring

---

## Questions to Consider

1. **API Authentication**: JWT tokens vs API keys? (Recommendation: API keys for simplicity)
2. **Rate Limiting**: Should API have rate limits? (Recommendation: Yes, prevent abuse)
3. **Caching**: Should API client cache responses? (Recommendation: No for now, keep simple)
4. **Monitoring**: What metrics to track? (Recommendation: API response times, error rates)
5. **Backwards Compatibility**: Keep old Database class? (Recommendation: Yes, for debug scripts)

---

## APPENDIX: Pattern Data Storage Migration

### Current State

Pattern learning data currently stored in JSON files:
- `data/comments.json` - All player comments with build orders (~650K lines)
- `data/patterns.json` - Learned patterns with signatures (~936K lines)
- `data/learning_stats.json` - Statistics about patterns
- `data/sc2_race_data.json` - Race-specific data

**Problems with JSON file storage:**
- No versioning/history
- Hard to query (must load entire file)
- Backup/restore complexity
- Concurrent access issues
- Large files (~1MB+) slow to load
- No relationship to replay data in MySQL

### Proposed: Move Pattern Data to MySQL

**Benefits:**
1. **Unified Storage**: All game data in one place
2. **Queryable**: Find patterns by opponent, race, date, similarity
3. **Relationships**: Link patterns to replays/players
4. **Performance**: Index on common queries
5. **Backup**: Single database backup includes everything
6. **Consistency**: ACID transactions ensure data integrity

### Schema Design

#### New Tables

```sql
-- Pattern library (learned build order patterns)
CREATE TABLE Patterns (
    Id INT AUTO_INCREMENT PRIMARY KEY,
    Pattern_Name VARCHAR(50) UNIQUE NOT NULL,  -- pattern_001, pattern_002, etc.
    Comment TEXT NOT NULL,                      -- Human description
    Keywords JSON NOT NULL,                     -- Array of keywords
    Race ENUM('Terran', 'Protoss', 'Zerg', 'Unknown') NOT NULL,
    Signature JSON NOT NULL,                    -- Build order signature (early_game, mid_game, late_game)
    Confidence DECIMAL(3,2) DEFAULT 0.80,       -- AI confidence score
    Occurrences INT DEFAULT 1,                  -- How many times seen
    First_Seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    Last_Seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_race (Race),
    INDEX idx_last_seen (Last_Seen),
    FULLTEXT idx_keywords (Comment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player comments with full build orders
CREATE TABLE Player_Comments (
    Id INT AUTO_INCREMENT PRIMARY KEY,
    Comment_Id VARCHAR(50) UNIQUE NOT NULL,     -- comment_001, comment_002, etc.
    Replay_Id INT,                               -- Link to Replays table (nullable for legacy)
    Comment TEXT NOT NULL,                       -- Player's strategic comment
    Raw_Comment TEXT,                            -- Original unprocessed comment
    Cleaned_Comment TEXT,                        -- Processed comment
    Keywords JSON NOT NULL,                      -- Array of extracted keywords
    Game_Data JSON NOT NULL,                     -- Opponent, race, map, result, duration, date
    Build_Order JSON NOT NULL,                   -- Full build order array
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (Replay_Id) REFERENCES Replays(Id) ON DELETE SET NULL,
    INDEX idx_comment_id (Comment_Id),
    INDEX idx_replay_id (Replay_Id),
    FULLTEXT idx_comment (Comment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pattern statistics
CREATE TABLE Pattern_Stats (
    Id INT AUTO_INCREMENT PRIMARY KEY,
    Stat_Key VARCHAR(100) NOT NULL,              -- 'total_keywords', 'race_Protoss', etc.
    Stat_Value JSON NOT NULL,                    -- Flexible value storage
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_stat (Stat_Key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pattern to Comment relationships (many-to-many)
CREATE TABLE Pattern_Comment_Links (
    Id INT AUTO_INCREMENT PRIMARY KEY,
    Pattern_Id INT NOT NULL,
    Comment_Id INT NOT NULL,
    Similarity_Score DECIMAL(5,4),               -- 0.0000 to 1.0000
    
    FOREIGN KEY (Pattern_Id) REFERENCES Patterns(Id) ON DELETE CASCADE,
    FOREIGN KEY (Comment_Id) REFERENCES Player_Comments(Id) ON DELETE CASCADE,
    UNIQUE KEY unique_link (Pattern_Id, Comment_Id),
    INDEX idx_similarity (Similarity_Score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### IDatabaseClient Interface Additions

Add to the interface:

```python
# Pattern Operations
@abstractmethod
def get_all_patterns(self, race: Optional[str] = None) -> List[Dict]:
    """Get all learned patterns, optionally filtered by race"""
    pass

@abstractmethod
def get_pattern_by_name(self, pattern_name: str) -> Optional[Dict]:
    """Get specific pattern by name (pattern_001, etc.)"""
    pass

@abstractmethod
def save_pattern(self, pattern_data: Dict) -> int:
    """Save or update a pattern, returns pattern ID"""
    pass

@abstractmethod
def delete_pattern(self, pattern_name: str) -> bool:
    """Delete a pattern by name"""
    pass

@abstractmethod
def search_patterns_by_keywords(self, keywords: List[str]) -> List[Dict]:
    """Find patterns matching any of the keywords"""
    pass

# Comment Operations
@abstractmethod
def get_all_comments(self, limit: Optional[int] = None) -> List[Dict]:
    """Get all player comments with build orders"""
    pass

@abstractmethod
def get_comment_by_id(self, comment_id: str) -> Optional[Dict]:
    """Get specific comment by ID (comment_001, etc.)"""
    pass

@abstractmethod
def save_comment(self, comment_data: Dict) -> int:
    """Save a player comment with build order, returns comment DB ID"""
    pass

@abstractmethod
def link_pattern_to_comment(self, pattern_name: str, comment_id: str, similarity: float):
    """Create relationship between pattern and comment"""
    pass

# Stats Operations
@abstractmethod
def get_pattern_stats(self) -> Dict:
    """Get all pattern statistics"""
    pass

@abstractmethod
def update_pattern_stat(self, stat_key: str, stat_value: Any):
    """Update a specific statistic"""
    pass
```

### API Endpoints Additions

Add to `mathison-db-api/app/routers/patterns.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

router = APIRouter()

@router.get("/")
async def get_all_patterns(
    race: Optional[str] = Query(None, regex="^(Terran|Protoss|Zerg)$"),
    db: Database = Depends(get_db)
):
    """Get all patterns, optionally filtered by race"""
    return db.get_all_patterns(race)

@router.get("/{pattern_name}")
async def get_pattern(pattern_name: str, db: Database = Depends(get_db)):
    """Get specific pattern by name"""
    pattern = db.get_pattern_by_name(pattern_name)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern

@router.post("/")
async def create_or_update_pattern(
    pattern_data: dict,
    db: Database = Depends(get_db)
):
    """Create or update a pattern"""
    pattern_id = db.save_pattern(pattern_data)
    return {"pattern_id": pattern_id, "success": True}

@router.delete("/{pattern_name}")
async def delete_pattern(pattern_name: str, db: Database = Depends(get_db)):
    """Delete a pattern"""
    success = db.delete_pattern(pattern_name)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return {"success": True}

@router.get("/search/keywords")
async def search_by_keywords(
    keywords: List[str] = Query(...),
    db: Database = Depends(get_db)
):
    """Search patterns by keywords"""
    return db.search_patterns_by_keywords(keywords)
```

Add to `mathison-db-api/app/routers/comments.py`:

```python
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_all_comments(
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: Database = Depends(get_db)
):
    """Get all player comments"""
    return db.get_all_comments(limit)

@router.get("/{comment_id}")
async def get_comment(comment_id: str, db: Database = Depends(get_db)):
    """Get specific comment by ID"""
    comment = db.get_comment_by_id(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

@router.post("/")
async def create_comment(comment_data: dict, db: Database = Depends(get_db)):
    """Save a player comment"""
    comment_id = db.save_comment(comment_data)
    return {"comment_id": comment_id, "success": True}

@router.post("/link")
async def link_pattern_to_comment(
    pattern_name: str,
    comment_id: str,
    similarity: float = Query(..., ge=0.0, le=1.0),
    db: Database = Depends(get_db)
):
    """Link a pattern to a comment with similarity score"""
    db.link_pattern_to_comment(pattern_name, comment_id, similarity)
    return {"success": True}
```

### Migration Strategy for Pattern Data

#### Option A: Separate Migration (Recommended)

Keep this as **Phase 7** - separate from the initial database API migration:

1. Get database API working with replay/player data first
2. Once stable, add pattern tables and methods
3. Create migration script to import JSON → MySQL
4. Update SC2PatternLearner to use database
5. Keep JSON files as backup during transition

**Timeline**: Do this AFTER Phase 1-6 are complete and stable.

#### Option B: Include in Initial Migration

Add pattern support to the API from the start, but don't migrate the data yet:
- Schema exists in database
- API endpoints defined
- Methods in interface (return empty for now)
- Migrate data later when ready

**Recommendation**: **Option A** - Separate migration

**Reasoning:**
- Pattern data is complex (~1.5M lines of JSON)
- SC2PatternLearner has intricate logic
- Want to validate database API with simpler data first
- Can test thoroughly before touching pattern system
- Lower risk - pattern system is critical

### Preparation for Future Pattern Migration

In the **current** database API migration, include:

1. **Schema**: Create tables (empty for now)
2. **Interface methods**: Define but return placeholder/empty
3. **API endpoints**: Implement but data source is empty
4. **Documentation**: Note "Pattern data migration is Phase 7"

This way the API is **ready** for pattern data, but we don't have to migrate it yet.

### Pattern Migration Script (For Phase 7)

```python
# utils/migrate_patterns_to_db.py

"""
Migrate data/comments.json and data/patterns.json to MySQL database.
Run this AFTER database API is stable.
"""

import json
from adapters.database.database_client_factory import create_database_client

def migrate_patterns():
    """Migrate patterns.json to Patterns table"""
    db = create_database_client()
    
    with open('data/patterns.json', 'r') as f:
        patterns = json.load(f)
    
    print(f"Migrating {len(patterns)} patterns...")
    for pattern_name, pattern_data in patterns.items():
        db.save_pattern({
            'pattern_name': pattern_name,
            'comment': pattern_data.get('comment', ''),
            'keywords': pattern_data.get('keywords', []),
            'race': pattern_data.get('race', 'Unknown'),
            'signature': pattern_data.get('signature', {}),
            'confidence': pattern_data.get('confidence', 0.8),
            # ... other fields
        })
    print("Pattern migration complete!")

def migrate_comments():
    """Migrate comments.json to Player_Comments table"""
    db = create_database_client()
    
    with open('data/comments.json', 'r') as f:
        data = json.load(f)
    
    comments = data.get('comments', [])
    print(f"Migrating {len(comments)} comments...")
    
    for comment in comments:
        db.save_comment(comment)
    
    print("Comment migration complete!")

if __name__ == "__main__":
    import sys
    if '--confirm' not in sys.argv:
        print("This will migrate JSON pattern data to MySQL")
        print("Run with --confirm to proceed")
        sys.exit(1)
    
    migrate_patterns()
    migrate_comments()
```

### Updated Estimated Effort

- **Phase 1-6** (Database API for replays/players): ~30-40 hours
- **Phase 7** (Pattern data migration): +15-20 hours
  - Schema implementation: 2-3 hours
  - Database methods: 3-4 hours
  - API endpoints: 2-3 hours
  - Migration script: 2-3 hours
  - Update SC2PatternLearner: 4-6 hours
  - Testing: 2-3 hours

**Total with Pattern Migration**: ~45-60 hours

### Recommendation

**Yes, include pattern storage in the API design**, but migrate the actual data separately:

1. **Now (Phase 1-6)**: Database API for replays/players
2. **Later (Phase 7)**: Pattern data migration (separate task, safer testing)

This gives you:
- ✅ API ready for patterns when you want them
- ✅ Can test database API thoroughly first
- ✅ Lower risk (don't touch critical pattern system yet)
- ✅ Pattern JSON files continue working during transition
- ✅ Can roll back easily if issues

---

## CRITICAL: Dual-Mode Support for Pattern Data

### The Requirement

**Both modes must work independently and simultaneously:**

| Mode | Replay Data | Pattern Data |
|------|-------------|--------------|
| **Local** | Direct MySQL connection | Local JSON files (`data/*.json`) |
| **API** | Remote MySQL via REST API | Remote pattern storage via API |

**Key point**: When `DB_MODE="local"`, the system uses:
- LocalDatabaseClient for replay/player data
- **Local JSON files** for pattern data

When `DB_MODE="api"`, the system uses:
- ApiDatabaseClient for replay/player data  
- **API calls** for pattern data

### Pattern Storage Abstraction

Create an interface for pattern storage (similar to database):

**File**: `core/interfaces/i_pattern_storage.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class IPatternStorage(ABC):
    """
    Interface for pattern/comment storage.
    Implementations can use JSON files or API.
    """
    
    @abstractmethod
    def load_patterns(self) -> Dict:
        """Load all patterns"""
        pass
    
    @abstractmethod
    def save_patterns(self, patterns: Dict) -> bool:
        """Save all patterns"""
        pass
    
    @abstractmethod
    def load_comments(self) -> Dict:
        """Load all comments"""
        pass
    
    @abstractmethod
    def save_comments(self, comments: Dict) -> bool:
        """Save all comments"""
        pass
    
    @abstractmethod
    def load_stats(self) -> Dict:
        """Load learning statistics"""
        pass
    
    @abstractmethod
    def save_stats(self, stats: Dict) -> bool:
        """Save learning statistics"""
        pass
```

### Implementation: File-Based Storage (Current)

**File**: `adapters/patterns/file_pattern_storage.py`

```python
import json
import os
from core.interfaces.i_pattern_storage import IPatternStorage
from settings import config

class FilePatternStorage(IPatternStorage):
    """
    File-based pattern storage using local JSON files.
    This is the current behavior.
    """
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or config.PATTERN_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_patterns(self) -> Dict:
        """Load patterns from data/patterns.json"""
        patterns_file = os.path.join(self.data_dir, 'patterns.json')
        if not os.path.exists(patterns_file):
            return {}
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_patterns(self, patterns: Dict) -> bool:
        """Save patterns to data/patterns.json"""
        patterns_file = os.path.join(self.data_dir, 'patterns.json')
        try:
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving patterns: {e}")
            return False
    
    def load_comments(self) -> Dict:
        """Load comments from data/comments.json"""
        comments_file = os.path.join(self.data_dir, 'comments.json')
        if not os.path.exists(comments_file):
            return {"comments": [], "keyword_index": {}}
        
        with open(comments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_comments(self, comments: Dict) -> bool:
        """Save comments to data/comments.json"""
        comments_file = os.path.join(self.data_dir, 'comments.json')
        try:
            with open(comments_file, 'w', encoding='utf-8') as f:
                json.dump(comments, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving comments: {e}")
            return False
    
    def load_stats(self) -> Dict:
        """Load stats from data/learning_stats.json"""
        stats_file = os.path.join(self.data_dir, 'learning_stats.json')
        if not os.path.exists(stats_file):
            return {"total_keywords": 0, "keyword_breakdown": {}}
        
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_stats(self, stats: Dict) -> bool:
        """Save stats to data/learning_stats.json"""
        stats_file = os.path.join(self.data_dir, 'learning_stats.json')
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving stats: {e}")
            return False
```

### Implementation: API-Based Storage (New)

**File**: `adapters/patterns/api_pattern_storage.py`

```python
import requests
from typing import Dict
from core.interfaces.i_pattern_storage import IPatternStorage
from settings import config

class ApiPatternStorage(IPatternStorage):
    """
    API-based pattern storage using remote database service.
    Used when DB_MODE="api".
    """
    
    def __init__(self, api_base_url: str = None, api_key: str = None):
        self.api_base_url = api_base_url or config.DB_API_URL
        self.api_key = api_key or config.DB_API_KEY
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: dict = None):
        """Generic API request"""
        url = f"{self.api_base_url}{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url, params=data, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API pattern request failed: {method} {endpoint} - {e}")
            raise
    
    def load_patterns(self) -> Dict:
        """Load patterns from API"""
        patterns_list = self._make_request('GET', '/api/v1/patterns')
        
        # Convert list of patterns to dict format (for backward compatibility)
        patterns_dict = {}
        for pattern in patterns_list:
            pattern_name = pattern.get('pattern_name')
            if pattern_name:
                patterns_dict[pattern_name] = pattern
        
        return patterns_dict
    
    def save_patterns(self, patterns: Dict) -> bool:
        """Save patterns to API (batch save)"""
        try:
            for pattern_name, pattern_data in patterns.items():
                self._make_request('POST', '/api/v1/patterns', {
                    'pattern_name': pattern_name,
                    **pattern_data
                })
            return True
        except Exception as e:
            print(f"Error saving patterns via API: {e}")
            return False
    
    def load_comments(self) -> Dict:
        """Load comments from API"""
        comments_list = self._make_request('GET', '/api/v1/comments')
        
        # Convert to expected format
        return {
            "comments": comments_list,
            "keyword_index": {}  # Can be rebuilt if needed
        }
    
    def save_comments(self, comments: Dict) -> bool:
        """Save comments to API (batch save)"""
        try:
            comments_list = comments.get('comments', [])
            for comment in comments_list:
                self._make_request('POST', '/api/v1/comments', comment)
            return True
        except Exception as e:
            print(f"Error saving comments via API: {e}")
            return False
    
    def load_stats(self) -> Dict:
        """Load stats from API"""
        return self._make_request('GET', '/api/v1/patterns/stats')
    
    def save_stats(self, stats: Dict) -> bool:
        """Save stats to API"""
        try:
            self._make_request('POST', '/api/v1/patterns/stats', stats)
            return True
        except Exception as e:
            print(f"Error saving stats via API: {e}")
            return False
```

### Pattern Storage Factory

**File**: `adapters/patterns/pattern_storage_factory.py`

```python
from core.interfaces.i_pattern_storage import IPatternStorage
from adapters.patterns.file_pattern_storage import FilePatternStorage
from adapters.patterns.api_pattern_storage import ApiPatternStorage
from settings import config
import logging

logger = logging.getLogger("PatternStorageFactory")

def create_pattern_storage() -> IPatternStorage:
    """
    Factory function to create the appropriate pattern storage
    based on configuration (matches DB_MODE).
    
    Returns:
        IPatternStorage: Either FilePatternStorage or ApiPatternStorage
    """
    storage_mode = config.DB_MODE.lower()
    
    if storage_mode == "local":
        logger.info("Creating FilePatternStorage (local JSON files)")
        return FilePatternStorage(data_dir=config.PATTERN_DATA_DIR)
    
    elif storage_mode == "api":
        logger.info(f"Creating ApiPatternStorage (API URL: {config.DB_API_URL})")
        return ApiPatternStorage(
            api_base_url=config.DB_API_URL,
            api_key=config.DB_API_KEY
        )
    
    else:
        raise ValueError(f"Invalid DB_MODE: {storage_mode}. Must be 'local' or 'api'")
```

### Update SC2PatternLearner

**File**: `api/pattern_learning.py` (modifications)

```python
class SC2PatternLearner:
    def __init__(self, db, logger, pattern_storage=None):
        self.db = db
        self.logger = logger
        self.patterns = defaultdict(list)
        self.comment_keywords = defaultdict(list)
        
        # Use provided storage or create from factory
        if pattern_storage is None:
            from adapters.patterns.pattern_storage_factory import create_pattern_storage
            self.pattern_storage = create_pattern_storage()
        else:
            self.pattern_storage = pattern_storage
        
        # Load existing patterns
        self.load_patterns_from_storage()
    
    def load_patterns_from_storage(self):
        """Load patterns using the storage interface (file or API)"""
        try:
            # Load from storage (abstracts file vs API)
            patterns_data = self.pattern_storage.load_patterns()
            comments_data = self.pattern_storage.load_comments()
            
            # Process patterns...
            # (existing logic stays the same)
            
        except Exception as e:
            self.logger.error(f"Error loading patterns from storage: {e}")
    
    def save_patterns_to_storage(self):
        """Save patterns using the storage interface (file or API)"""
        try:
            # Prepare data
            patterns_dict = self._prepare_patterns_for_save()
            comments_dict = self._prepare_comments_for_save()
            stats_dict = self._prepare_stats_for_save()
            
            # Save via storage (abstracts file vs API)
            self.pattern_storage.save_patterns(patterns_dict)
            self.pattern_storage.save_comments(comments_dict)
            self.pattern_storage.save_stats(stats_dict)
            
        except Exception as e:
            self.logger.error(f"Error saving patterns to storage: {e}")
```

### Update Configuration

**File**: `settings/config.example.py`

```python
"""
||   Pattern Data Storage
"""
# Pattern data directory (used when DB_MODE='local')
PATTERN_DATA_DIR = "data"

# When DB_MODE='api', patterns are also stored remotely via the API
# No separate PATTERN_MODE needed - it follows DB_MODE automatically
```

### Update run_core.py

```python
# Old:
from api.pattern_learning import SC2PatternLearner
pattern_learner = SC2PatternLearner(db, logger)

# New:
from adapters.patterns.pattern_storage_factory import create_pattern_storage
from api.pattern_learning import SC2PatternLearner

pattern_storage = create_pattern_storage()  # Matches DB_MODE
pattern_learner = SC2PatternLearner(db_client, logger, pattern_storage)
```

### Testing Both Modes

#### Test Local Mode (Current Behavior)
```python
# config.py
DB_MODE = "local"
DB_HOST = "localhost"
PATTERN_DATA_DIR = "data"

# Result:
# - Replay data: Direct MySQL
# - Pattern data: data/patterns.json, data/comments.json (local files)
```

#### Test API Mode (Remote)
```python
# config.py
DB_MODE = "api"
DB_API_URL = "https://api.mathison.psistorm.com"
DB_API_KEY = "prod-key"

# Result:
# - Replay data: API → Remote MySQL
# - Pattern data: API → Remote MySQL (patterns tables)
```

#### Test Mixed (for debugging)
You could even add a `PATTERN_MODE` config if you want independent control:
```python
DB_MODE = "local"        # Replay data uses local MySQL
PATTERN_MODE = "api"     # Pattern data uses remote API

# (Not recommended for production, but useful for testing migration)
```

### Migration Impact Summary

| Component | Local Mode | API Mode |
|-----------|------------|----------|
| **Replay Data** | Direct MySQL | API → Remote MySQL |
| **Player Data** | Direct MySQL | API → Remote MySQL |
| **Pattern Data** | JSON files | API → Remote MySQL |
| **Comments Data** | JSON files | API → Remote MySQL |
| **Stats Data** | JSON files | API → Remote MySQL |

**Key**: One config setting (`DB_MODE`) controls everything.

### Backward Compatibility

✅ **Existing local setup keeps working:**
- `DB_MODE="local"` (or unset, defaults to local)
- Direct MySQL connection
- JSON files in `data/` folder
- Zero changes needed

✅ **Can switch to API mode anytime:**
- Change `DB_MODE="api"`
- Point to API server
- Everything works remotely

✅ **Can switch back to local:**
- Change `DB_MODE="local"`
- Works with local files again
- No data loss (assuming you synced)

### Simplified Error Handling (No Automatic Fallbacks)

**Philosophy**: Pick a mode and stick with it. If it fails, stop and tell the user.

```python
# In factory methods and storage classes:

def create_database_client() -> IDatabaseClient:
    db_mode = config.DB_MODE.lower()
    
    if db_mode == "local":
        logger.info("Database Mode: LOCAL (Direct MySQL)")
        try:
            return LocalDatabaseClient()
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to local MySQL database: {e}")
            logger.error("Check DB_HOST, DB_USER, DB_PASSWORD in config.py")
            raise SystemExit("Cannot start - Local database connection failed")
    
    elif db_mode == "api":
        logger.info(f"Database Mode: API (Remote: {config.DB_API_URL})")
        try:
            client = ApiDatabaseClient()
            # Test the connection
            client._make_request('GET', '/health')
            return client
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to database API: {e}")
            logger.error(f"Check DB_API_URL ({config.DB_API_URL}) and DB_API_KEY in config.py")
            raise SystemExit("Cannot start - API connection failed")
    
    else:
        logger.error(f"FATAL: Invalid DB_MODE: '{db_mode}'. Must be 'local' or 'api'")
        raise SystemExit("Cannot start - Invalid configuration")

# Same approach for pattern storage:

def create_pattern_storage() -> IPatternStorage:
    storage_mode = config.DB_MODE.lower()  # Uses same mode as database
    
    if storage_mode == "local":
        logger.info("Pattern Storage: LOCAL (JSON files)")
        try:
            storage = FilePatternStorage()
            # Verify data directory exists
            if not os.path.exists(storage.data_dir):
                os.makedirs(storage.data_dir, exist_ok=True)
            return storage
        except Exception as e:
            logger.error(f"FATAL: Failed to initialize local pattern storage: {e}")
            logger.error(f"Check PATTERN_DATA_DIR ({config.PATTERN_DATA_DIR}) is writable")
            raise SystemExit("Cannot start - Pattern storage initialization failed")
    
    elif storage_mode == "api":
        logger.info(f"Pattern Storage: API (Remote: {config.DB_API_URL})")
        try:
            storage = ApiPatternStorage()
            # Test the connection
            storage._make_request('GET', '/health')
            return storage
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to pattern storage API: {e}")
            logger.error(f"Check DB_API_URL ({config.DB_API_URL}) and DB_API_KEY in config.py")
            raise SystemExit("Cannot start - API connection failed")
    
    else:
        logger.error(f"FATAL: Invalid DB_MODE: '{storage_mode}'")
        raise SystemExit("Cannot start - Invalid configuration")
```

### Error Behavior Examples

#### Scenario 1: Local Mode, MySQL Down
```
ERROR: FATAL: Failed to connect to local MySQL database: Can't connect to MySQL server on 'localhost'
ERROR: Check DB_HOST, DB_USER, DB_PASSWORD in config.py
FATAL: Cannot start - Local database connection failed

[Bot exits]
```

**User Action**: Fix MySQL, check credentials, or switch to API mode

#### Scenario 2: API Mode, API Server Down
```
ERROR: FATAL: Failed to connect to database API: Connection refused
ERROR: Check DB_API_URL (https://api.mathison.psistorm.com) and DB_API_KEY in config.py
FATAL: Cannot start - API connection failed

[Bot exits]
```

**User Action**: Check API server, verify URL/key, or switch to local mode

#### Scenario 3: Invalid Configuration
```
ERROR: FATAL: Invalid DB_MODE: 'remote'. Must be 'local' or 'api'
FATAL: Cannot start - Invalid configuration

[Bot exits]
```

**User Action**: Fix typo in config.py

### No Fallbacks, No Transitions

**What we DON'T do:**
- ❌ Try API, fall back to local on failure
- ❌ Automatically switch modes during runtime
- ❌ Use local cache when API is slow
- ❌ Sync between local and remote
- ❌ "Smart" mode detection

**What we DO:**
- ✅ Use exactly what's configured
- ✅ Fail loudly and clearly
- ✅ Stop immediately on error
- ✅ Tell user exactly what's wrong
- ✅ Let user decide next action

### Mode Switching is Manual

```python
# To switch from local to API:
1. Stop the bot
2. Edit config.py: DB_MODE = "api"
3. Start the bot
4. If it fails, read the error and fix it

# To switch from API to local:
1. Stop the bot
2. Edit config.py: DB_MODE = "local"
3. Start the bot
4. If it fails, read the error and fix it
```

### Startup Logging (Clear Mode Indication)

```
====================================
Mathison Bot Starting
====================================
Configuration:
  DB_MODE: local
  Database: Direct MySQL (localhost)
  Patterns: Local JSON (data/)
====================================
Initializing database connection...
SUCCESS: Connected to local MySQL
Initializing pattern storage...
SUCCESS: Pattern storage ready
====================================
Bot ready!
```

Or for API mode:
```
====================================
Mathison Bot Starting
====================================
Configuration:
  DB_MODE: api
  Database: Remote API (https://api.mathison.psistorm.com)
  Patterns: Remote API (https://api.mathison.psistorm.com)
====================================
Initializing database connection...
Testing API connection to https://api.mathison.psistorm.com/health...
SUCCESS: API connection verified
Initializing pattern storage...
SUCCESS: Pattern storage ready
====================================
Bot ready!
```

### Simple Deployment Checklist

#### For Local Mode:
- [ ] `DB_MODE = "local"`
- [ ] MySQL running locally
- [ ] `DB_HOST`, `DB_USER`, `DB_PASSWORD` correct
- [ ] `data/` folder exists and writable

#### For API Mode:
- [ ] `DB_MODE = "api"`
- [ ] API server running and accessible
- [ ] `DB_API_URL` points to correct server
- [ ] `DB_API_KEY` is valid
- [ ] Network connectivity to API server

**That's it. No magic, no fallbacks, no complexity.**

