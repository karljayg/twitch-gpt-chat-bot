# Mathison Database API Specification

**Version**: 1.0  
**Last Updated**: 2026-01-27

## Overview

This REST API provides secure access to the Mathison StarCraft II database, allowing external applications to query player data, replay information, comments, and patterns.

## Base URL

```
https://psistorm.com/api-server/public
```

## Authentication

All API requests (except `/health`) require Bearer token authentication.

### Headers Required

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Obtaining an API Key

Contact the database administrator to receive your unique API key. Keep this key secure and never commit it to version control.

## Rate Limiting

- **Rate Limit**: 100 requests per minute per API key
- **Burst Limit**: 20 requests per second

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Total requests allowed per minute
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Response Format

All responses return JSON with appropriate HTTP status codes.

### Success Response
```json
{
  "data": { ... },
  "timestamp": 1737972000
}
```

### Error Response
```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "details": "Additional context (optional)"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (missing/invalid parameters)
- `401` - Unauthorized (invalid or missing API key)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

---

## Endpoints

### Health Check

Check API availability and database connection status.

**Endpoint**: `GET /health`  
**Authentication**: Not required

#### Response
```json
{
  "status": "healthy",
  "timestamp": 1737972000,
  "database": "connected",
  "api_version": "v1"
}
```

---

## Player Endpoints

### 1. Check Player and Race Exists

Get the last game data for a player with specific race.

**Endpoint**: `GET /api/v1/players/check`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_name` | string | Yes | Player's StarCraft II username |
| `player_race` | string | Yes | Race: `Protoss`, `Terran`, or `Zerg` |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/check?player_name=Atlantis&player_race=Protoss" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
{
  "UnixTimestamp": 1769521490,
  "ReplayId": 24943,
  "Player1_Id": 43959,
  "Player2_Id": 58,
  "Player1_Name": "Atlantis",
  "Player2_Name": "KJ",
  "Player1_PickRace": "Protoss",
  "Player2_PickRace": "Terran",
  "Player1_Race": "Protoss",
  "Player2_Race": "Terran",
  "Player1_Result": "Lose",
  "Player2_Result": "Win",
  "Date_Uploaded": "2026-01-27 13:45:02",
  "Date_Played": "2026-01-27 08:44:50",
  "Replay_Summary": "Players: Atlantis: Protoss, KJ: Terran\nMap: Winter Madness LE...",
  "Player_Comments": "1 base prism stalkers all in",
  "Map": "Winter Madness LE",
  "Region": "eu",
  "GameType": "1v1",
  "GameDuration": "5m 45s"
}
```

---

### 2. Check Player Exists

Check if a player exists in the database (any race).

**Endpoint**: `GET /api/v1/players/{player_name}/exists`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_name` | string | Yes | Player's username |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/exists" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
{
  "exists": true,
  "data": {
    "Id": 43959,
    "SC2_UserId": "Atlantis"
  }
}
```

---

### 3. Get Player Records

Get win/loss records for a player.

**Endpoint**: `GET /api/v1/players/{player_name}/records`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_name` | string | Yes | Player's username |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/records" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
[
  "vs KJ (Terran): 0-2",
  "as Protoss: 0-2"
]
```

---

### 4. Get Player Comments

Get all saved comments for a player with specific race.

**Endpoint**: `GET /api/v1/players/{player_name}/comments`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_name` | string | Yes | Player's username |

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `race` | string | Yes | Race: `Protoss`, `Terran`, or `Zerg` |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/comments?race=Protoss" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
[
  {
    "Id": 1234,
    "OpponentName": "Atlantis",
    "Race": "Protoss",
    "Comment": "1 base prism stalkers all in",
    "Date": "2026-01-27 08:45:00",
    "Map": "Winter Madness LE",
    "Result": "Victory"
  }
]
```

---

### 5. Get Player Overall Records

Get overall win/loss statistics for a player.

**Endpoint**: `GET /api/v1/players/{player_name}/overall_records`

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/overall_records" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
{
  "records": "Overall: 15-8 (65% win rate)"
}
```

---

### 6. Get Race Matchup Records

Get win/loss records broken down by race matchups.

**Endpoint**: `GET /api/v1/players/{player_name}/race_matchup_records`

#### Example Response
```json
{
  "records": "PvT: 5-3, PvP: 6-2, PvZ: 4-3"
}
```

---

### 7. Get Head-to-Head Matchup

Get head-to-head records between two players.

**Endpoint**: `GET /api/v1/players/head_to_head`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player1` | string | Yes | First player's username |
| `player2` | string | Yes | Second player's username |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/head_to_head?player1=KJ&player2=Atlantis" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
[
  "KJ vs Atlantis: 2-0",
  "Last played: 2026-01-27"
]
```

---

## Replay Endpoints

### 8. Get Last Replay Info

Get the most recent replay in the database.

**Endpoint**: `GET /api/v1/replays/last`

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/replays/last" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
{
  "ReplayId": 24943,
  "Player1_Name": "Atlantis",
  "Player2_Name": "KJ",
  "Map": "Winter Madness LE",
  "Date_Played": "2026-01-27 08:44:50",
  "GameDuration": "5m 45s",
  "Player_Comments": "1 base prism stalkers all in"
}
```

---

### 9. Get Latest Replay (Processed)

Get the latest replay with processed opponent data.

**Endpoint**: `GET /api/v1/replays/latest`

#### Example Response
```json
{
  "opponent": "Atlantis",
  "map": "Winter Madness LE",
  "result": "Win",
  "date": "2026-01-27",
  "duration": "5m 45s",
  "timestamp": 1769521490,
  "existing_comment": "1 base prism stalkers all in"
}
```

---

### 10. Get Replay by ID

Get a specific replay by its ID.

**Endpoint**: `GET /api/v1/replays/{replay_id}`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `replay_id` | integer | Yes | Replay ID |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/replays/24943" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 11. Get Games from Last X Hours

Get all games played within the last X hours.

**Endpoint**: `GET /api/v1/replays/games`

#### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | integer | No | 24 | Number of hours to look back |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/replays/games?hours=12" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
[
  "2026-01-27 08:44:50 - KJ (Terran) vs Atlantis (Protoss) - Winter Madness LE - 5m 45s - KJ won",
  "2026-01-27 07:30:15 - KJ (Terran) vs Player2 (Zerg) - Acolyte LE - 8m 12s - KJ won"
]
```

---

### 12. Extract Opponent Build Order

Extract build order from the last game against a specific opponent.

**Endpoint**: `GET /api/v1/build_orders/extract`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `opponent_name` | string | Yes | Opponent's username |
| `opponent_race` | string | Yes | Opponent's race |
| `streamer_race` | string | Yes | Your race in that game |

#### Example Request
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/build_orders/extract?opponent_name=Atlantis&opponent_race=Protoss&streamer_race=Terran" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Example Response
```json
[
  "0:21 - Pylon",
  "0:43 - Gateway",
  "0:48 - Assimilator",
  "1:24 - Pylon",
  "1:32 - CyberneticsCore"
]
```

---

### 13. Insert Replay

Add a new replay to the database.

**Endpoint**: `POST /api/v1/replays`

#### Request Body
```json
{
  "replay_summary": "Players: Atlantis: Protoss, KJ: Terran\nMap: Winter Madness LE\nRegion: eu\nGame Type: 1v1\nTimestamp: 1769521490\nWinners: KJ\nLosers: Atlantis\nGame Duration: 5m 45s\n..."
}
```

#### Example Request
```bash
curl -X POST "https://psistorm.com/api-server/public/api/v1/replays" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"replay_summary": "Players: ...full summary..."}'
```

#### Example Response
```json
{
  "success": true,
  "replay_id": 24944
}
```

---

### 14. Update Last Replay Comment

Update the comment for the most recent replay.

**Endpoint**: `PUT /api/v1/replays/last/comment`

#### Request Body
```json
{
  "comment": "1 base prism stalkers all in"
}
```

#### Example Response
```json
{
  "success": true,
  "rows_affected": 1
}
```

---

## Comment & Pattern Endpoints

### 15. Save Player Comment

Save a comment with full game data to the PlayerComments table.

**Endpoint**: `POST /api/v1/comments/save`

#### Request Body
```json
{
  "comment_data": {
    "opponent_name": "Atlantis",
    "opponent_race": "Protoss",
    "comment": "1 base prism stalkers all in",
    "map": "Winter Madness LE",
    "date": 1769521490,
    "result": "Victory",
    "keywords": ["prism", "stalker", "all in"],
    "build_order": [
      {"time": "0:21", "name": "Pylon", "supply": 14},
      {"time": "0:43", "name": "Gateway", "supply": 16}
    ]
  }
}
```

#### Example Response
```json
{
  "success": true,
  "comment_id": 1235
}
```

---

### 16. Save Pattern

Save a learned pattern to the PatternLearning table.

**Endpoint**: `POST /api/v1/patterns/save`

#### Request Body
```json
{
  "pattern_entry": {
    "opponent_name": "Atlantis",
    "opponent_race": "Protoss",
    "comment": "1 base prism stalkers all in",
    "keywords": ["prism", "stalker", "all in", "1 base"],
    "map": "Winter Madness LE",
    "date": 1769521490,
    "result": "Victory"
  }
}
```

#### Example Response
```json
{
  "success": true,
  "pattern_id": 456
}
```

---

## Database Schema Reference

### Main Tables

#### `Replays` Table
Primary table for game replay data.

| Column | Type | Description |
|--------|------|-------------|
| `ReplayId` | INT | Primary key |
| `UnixTimestamp` | BIGINT | Unix timestamp of game |
| `Player1_Id` | INT | Foreign key to Users |
| `Player2_Id` | INT | Foreign key to Users |
| `Player1_PickRace` | VARCHAR | Race picked by player 1 |
| `Player2_PickRace` | VARCHAR | Race picked by player 2 |
| `Player1_Result` | VARCHAR | Win/Lose |
| `Player2_Result` | VARCHAR | Win/Lose |
| `Replay_Summary` | TEXT | Full replay text summary |
| `Player_Comments` | TEXT | User comments about the game |
| `Map` | VARCHAR | Map name |
| `Region` | VARCHAR | Server region |
| `GameType` | VARCHAR | 1v1, 2v2, 3v3, 4v4 |
| `GameDuration` | VARCHAR | Game length (e.g., "5m 45s") |

#### `Users` Table
Player information.

| Column | Type | Description |
|--------|------|-------------|
| `Id` | INT | Primary key |
| `SC2_UserId` | VARCHAR | StarCraft II username |

#### `PlayerComments` Table
Detailed comments with keywords and build orders.

| Column | Type | Description |
|--------|------|-------------|
| `Id` | INT | Primary key |
| `OpponentName` | VARCHAR | Opponent username |
| `Race` | VARCHAR | Opponent race |
| `Comment` | TEXT | User comment |
| `Keywords` | JSON | Extracted keywords |
| `BuildOrder` | JSON | Build order steps |
| `Map` | VARCHAR | Map name |
| `Date` | DATETIME | Game date |
| `Result` | VARCHAR | Win/Loss |

#### `PatternLearning` Table
Machine learning patterns for strategy recognition.

| Column | Type | Description |
|--------|------|-------------|
| `Id` | INT | Primary key |
| `OpponentName` | VARCHAR | Opponent username |
| `Race` | VARCHAR | Opponent race |
| `Comment` | TEXT | Pattern description |
| `Keywords` | JSON | Pattern keywords |
| `Confidence` | FLOAT | Pattern match confidence |
| `DateLearned` | DATETIME | When pattern was learned |

---

## Code Examples

### Python
```python
import requests

API_BASE_URL = "https://psistorm.com/api-server/public"
API_KEY = "your_api_key_here"

def get_player_info(player_name, race):
    """Check if player exists with specific race"""
    url = f"{API_BASE_URL}/api/v1/players/check"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    params = {
        "player_name": player_name,
        "player_race": race
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Example usage
player_data = get_player_info("Atlantis", "Protoss")
if player_data:
    print(f"Last game: {player_data['Date_Played']}")
    print(f"Result: {player_data['Player1_Result']}")
```

### JavaScript (Node.js)
```javascript
const axios = require('axios');

const API_BASE_URL = 'https://psistorm.com/api-server/public';
const API_KEY = 'your_api_key_here';

async function getPlayerInfo(playerName, race) {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/players/check`, {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      params: {
        player_name: playerName,
        player_race: race
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.status);
    console.error(error.response?.data);
    return null;
  }
}

// Example usage
getPlayerInfo('Atlantis', 'Protoss')
  .then(data => {
    if (data) {
      console.log(`Last game: ${data.Date_Played}`);
      console.log(`Result: ${data.Player1_Result}`);
    }
  });
```

### cURL
```bash
#!/bin/bash

API_BASE_URL="https://psistorm.com/api-server/public"
API_KEY="your_api_key_here"

# Check player and race
curl -X GET "${API_BASE_URL}/api/v1/players/check?player_name=Atlantis&player_race=Protoss" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json"

# Get player comments
curl -X GET "${API_BASE_URL}/api/v1/players/Atlantis/comments?race=Protoss" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json"

# Save a new comment
curl -X POST "${API_BASE_URL}/api/v1/comments/save" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment_data": {
      "opponent_name": "Atlantis",
      "opponent_race": "Protoss",
      "comment": "Fast expand into immortal push",
      "map": "Winter Madness LE",
      "date": 1769521490,
      "result": "Victory"
    }
  }'
```

### PHP
```php
<?php

$API_BASE_URL = 'https://psistorm.com/api-server/public';
$API_KEY = 'your_api_key_here';

function getPlayerInfo($playerName, $race) {
    global $API_BASE_URL, $API_KEY;
    
    $url = $API_BASE_URL . '/api/v1/players/check?' . http_build_query([
        'player_name' => $playerName,
        'player_race' => $race
    ]);
    
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . $API_KEY,
        'Content-Type: application/json'
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200) {
        return json_decode($response, true);
    } else {
        echo "Error: $httpCode\n";
        echo $response;
        return null;
    }
}

// Example usage
$playerData = getPlayerInfo('Atlantis', 'Protoss');
if ($playerData) {
    echo "Last game: " . $playerData['Date_Played'] . "\n";
    echo "Result: " . $playerData['Player1_Result'] . "\n";
}
```

---

## Error Handling Best Practices

### 1. Always Check Status Codes
```python
response = requests.get(url, headers=headers)
if response.status_code != 200:
    print(f"API Error: {response.status_code}")
    print(response.json())
    return None
```

### 2. Handle Network Errors
```python
try:
    response = requests.get(url, headers=headers, timeout=10)
except requests.exceptions.Timeout:
    print("Request timed out")
except requests.exceptions.ConnectionError:
    print("Connection failed")
```

### 3. Validate API Key
```python
# Test with health endpoint first
response = requests.get(f"{API_BASE_URL}/health")
if response.status_code == 200:
    print("API is reachable")
```

### 4. Implement Retry Logic
```python
from time import sleep

def api_call_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:  # Rate limit
                sleep(60)  # Wait 1 minute
                continue
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            sleep(2 ** attempt)  # Exponential backoff
```

---

## Security Considerations

1. **Never commit API keys** - Use environment variables
2. **Use HTTPS only** - All requests must use HTTPS in production
3. **Rotate keys regularly** - Request new keys every 90 days
4. **IP whitelisting** - Contact admin to whitelist your server IPs
5. **Monitor usage** - Track your API calls to detect anomalies

---

## Support

For API key requests, bug reports, or feature requests:
- **Email**: admin@psistorm.com
- **Repository**: GitHub (internal)
- **Documentation**: This file

---

## Changelog

### Version 1.0 (2026-01-27)
- Initial API specification
- 16 endpoints documented
- Added code examples in Python, JavaScript, PHP, and cURL
- Added database schema reference
- Added error handling best practices
