# Mathison Database API

REST API for remote Mathison database access using Slim Framework.

## Quick Start

### 1. Install Dependencies

```bash
composer install
```

If you don't have Composer:
```bash
curl -sS https://getcomposer.org/installer | php
php composer.phar install
```

### 2. Configure

```bash
cp config.example.php config.php
nano config.php  # Edit with your MySQL credentials and API key
```

### 3. Test Locally

```bash
composer start
# Or: php -S localhost:8000 -t public
```

Visit: http://localhost:8000/health

### 4. Deploy to Server

```bash
# On your server
cd /var/www/html/
cp -r /path/to/api-server mathison-api
cd mathison-api
composer install --no-dev --optimize-autoloader
cp config.example.php config.php
nano config.php  # Configure
chmod 644 config.php  # Secure config
```

## API Endpoints

### Health Check (No Auth)
```bash
curl http://localhost:8000/health
```

### Players
```bash
# Check if player exists with specific race
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/players/check?player_name=TestPlayer&player_race=Protoss"

# Check if player exists
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/players/TestPlayer/exists"

# Get player records
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/players/TestPlayer/records"

# Get player comments
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/players/TestPlayer/comments?race=Protoss"

# Get overall records
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/players/TestPlayer/overall_records"
```

### Replays
```bash
# Get last replay
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/replays/last"

# Get specific replay
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/replays/123"
```

### Build Orders
```bash
# Extract opponent build order
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/build_orders/extract?opponent_name=Enemy&opponent_race=Protoss&streamer_race=Terran"
```

## Testing Connection

### 1. Test Health
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy","timestamp":...,"database":"connected","api_version":"v1"}`

### 2. Test Auth
```bash
# Without API key (should fail)
curl http://localhost:8000/api/v1/replays/last

# With API key (should work)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/replays/last
```

## Troubleshooting

### "Database connection failed"
- Check `config.php` credentials
- Verify MySQL is running: `systemctl status mysql`
- Test connection: `mysql -u USERNAME -p`

### "Unauthorized"
- Verify API key in config.php
- Check Authorization header format: `Bearer YOUR_KEY` (note the space)

### "404 Not Found" on all endpoints
- Enable mod_rewrite: `sudo a2enmod rewrite`
- Check Apache AllowOverride: should be `All` in virtual host config
- Restart Apache: `sudo systemctl restart apache2`

### Composer errors
```bash
# Update composer
composer self-update

# Clear cache
composer clear-cache

# Reinstall
rm -rf vendor composer.lock
composer install
```

## Development

Run local development server:
```bash
composer start
```

Or manually:
```bash
php -S localhost:8000 -t public
```

## Security Notes

- **Never commit config.php** (contains credentials)
- **Use HTTPS in production** (never HTTP)
- **Keep API key secret** (treat like a password)
- **Limit API access** (firewall rules if possible)

## File Structure

```
api-server/
├── composer.json           # Dependencies
├── public/
│   └── index.php          # Entry point
├── src/
│   ├── Database.php       # Database queries
│   ├── middleware/
│   │   └── AuthMiddleware.php
│   └── routes/
│       ├── players.php
│       └── replays.php
├── config.php             # Your config (gitignored)
└── README.md              # This file
```

## Next Steps

1. Test API locally
2. Configure bot to use API:
   - Set `DB_MODE = "api"` in bot's config.py
   - Set `DB_API_URL = "http://localhost:8000"` (or your server URL)
   - Set `DB_API_KEY = "your-api-key"`
3. Deploy to production server
4. Update bot config with production URL

