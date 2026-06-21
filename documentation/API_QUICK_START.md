# Mathison Database API - Quick Start Guide

Get up and running with the Mathison Database API in 5 minutes.

## 1. Get Your API Key

Contact the database administrator to receive your API key. You'll receive:
- API Key (Bearer token)
- Base URL: `https://psistorm.com/api-server/public`

## 2. Test the Connection

```bash
# Test without authentication (health check)
curl https://psistorm.com/api-server/public/health

# Expected response:
# {"status":"healthy","timestamp":1737972000,"database":"connected","api_version":"v1"}
```

## 3. Make Your First Authenticated Request

```bash
# Replace YOUR_API_KEY with your actual key
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/check?player_name=Atlantis&player_race=Protoss" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 4. Common Use Cases

### Check if Player Exists
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/exists" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Get Latest Replay
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/replays/latest" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Get Player Comments
```bash
curl -X GET "https://psistorm.com/api-server/public/api/v1/players/Atlantis/comments?race=Protoss" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Save a Comment
```bash
curl -X POST "https://psistorm.com/api-server/public/api/v1/comments/save" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "comment_data": {
      "opponent_name": "Atlantis",
      "opponent_race": "Protoss",
      "comment": "1 base prism stalkers all in",
      "map": "Winter Madness LE",
      "date": 1769521490,
      "result": "Victory"
    }
  }'
```

## 5. Integration Examples

### Python
```python
import requests
import os

API_BASE_URL = "https://psistorm.com/api-server/public"
API_KEY = os.environ.get('MATHISON_API_KEY')  # Store in environment variable

def get_player_data(player_name, race):
    response = requests.get(
        f"{API_BASE_URL}/api/v1/players/check",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"player_name": player_name, "player_race": race}
    )
    return response.json() if response.status_code == 200 else None

# Usage
data = get_player_data("Atlantis", "Protoss")
print(data)
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

const API_BASE_URL = 'https://psistorm.com/api-server/public';
const API_KEY = process.env.MATHISON_API_KEY;

async function getPlayerData(playerName, race) {
  const response = await axios.get(`${API_BASE_URL}/api/v1/players/check`, {
    headers: { 'Authorization': `Bearer ${API_KEY}` },
    params: { player_name: playerName, player_race: race }
  });
  return response.data;
}

// Usage
getPlayerData('Atlantis', 'Protoss').then(console.log);
```

## 6. Environment Setup

### Store API Key Securely

**Never commit your API key to version control!**

#### Bash (.bashrc or .bash_profile)
```bash
export MATHISON_API_KEY="your_api_key_here"
```

#### Python (.env file)
```
MATHISON_API_KEY=your_api_key_here
```

Then use `python-dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('MATHISON_API_KEY')
```

#### Node.js (.env file)
```
MATHISON_API_KEY=your_api_key_here
```

Then use `dotenv`:
```javascript
require('dotenv').config();
const API_KEY = process.env.MATHISON_API_KEY;
```

## 7. Common Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status (no auth) |
| `/api/v1/players/check` | GET | Get player + race last game |
| `/api/v1/players/{name}/exists` | GET | Check if player exists |
| `/api/v1/players/{name}/comments` | GET | Get player comments |
| `/api/v1/replays/latest` | GET | Get latest replay |
| `/api/v1/replays/games` | GET | Get recent games |
| `/api/v1/comments/save` | POST | Save new comment |
| `/api/v1/patterns/save` | POST | Save learned pattern |

## 8. Error Handling

All errors return JSON with `error` and `message` fields:

```json
{
  "error": "Bad Request",
  "message": "Missing required parameter: player_name"
}
```

Common HTTP codes:
- `200` - Success
- `400` - Bad request (check parameters)
- `401` - Invalid API key
- `404` - Not found
- `429` - Rate limit exceeded
- `500` - Server error

## 9. Rate Limits

- **100 requests per minute** per API key
- **20 requests per second** (burst)

If you hit the limit, wait 60 seconds and retry.

## 10. Next Steps

- Read the [Full API Specification](./API_SPECIFICATION.md) for all endpoints
- Check [Database Schema Reference](./API_SPECIFICATION.md#database-schema-reference)
- Review [Code Examples](./API_SPECIFICATION.md#code-examples) in multiple languages

## Need Help?

- **Full Documentation**: `documentation/API_SPECIFICATION.md`
- **Support Email**: admin@psistorm.com
- **Issues**: Contact your administrator
