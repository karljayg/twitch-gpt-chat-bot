# Server Deployment Guide

## Quick Deploy to Web Server

### 1. **Pull Latest Code**
```bash
cd /path/to/your/webserver/twitch-gpt-chat-bot
git pull origin main
```

### 2. **Navigate to API Directory**
```bash
cd api-server
```

### 3. **Copy Configuration**
```bash
cp config.example.php config.php
```

### 4. **Edit Configuration**
Edit `config.php` and set:
```php
$db_config = [
    'host'     => 'localhost',      // Your MySQL host
    'user'     => 'your_db_user',   // MySQL username
    'password' => 'your_db_pass',   // MySQL password
    'database' => 'mathison',       // Database name
    'charset'  => 'utf8mb4'
];

// Generate a secure random API key
$api_key = 'GENERATE-SECURE-RANDOM-KEY-HERE';
```

**Generate secure API key:**
```bash
openssl rand -base64 32
# Or use: head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32
```

### 5. **Install Dependencies**
```bash
composer install --no-dev
```

If you don't have composer:
```bash
# Download composer
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php
php -r "unlink('composer-setup.php');"

# Install dependencies
php composer.phar install --no-dev
```

### 6. **Set Permissions**
```bash
# Make sure web server can read files
chmod -R 755 .
# Protect config
chmod 600 config.php
```

### 7. **Configure Web Server**

#### Apache (.htaccess included)
- Ensure `mod_rewrite` is enabled
- The included `.htaccess` should work automatically
- Make sure `AllowOverride All` is set for this directory

#### Nginx
Add to your site config:
```nginx
location /api-server/ {
    try_files $uri $uri/ /api-server/public/index.php?$query_string;
}

location ~ ^/api-server/public/.*\.php$ {
    fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;  # Adjust PHP version
    fastcgi_index index.php;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
}
```

### 8. **Test the API**

Health check (no auth):
```bash
curl https://your-domain.com/api-server/public/health
```

Expected response:
```json
{"status":"healthy","timestamp":1234567890,"database":"connected","api_version":"v1"}
```

Test authenticated endpoint:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-domain.com/api-server/public/api/v1/replays/last
```

### 9. **Run PHP Tests (Optional)**
```bash
./vendor/bin/phpunit tests/api_test.php
```

---

## Update Bot Configuration

On your local bot PC, edit `settings/config.py`:

```python
# Switch to API mode
DB_MODE = "api"

# Point to your server
DB_API_URL = "https://your-domain.com/api-server/public"
DB_API_KEY = "YOUR_API_KEY_FROM_CONFIG_PHP"
```

Restart the bot and verify it connects!

---

## Security Checklist

- [ ] `config.php` has restrictive permissions (600)
- [ ] Strong random API key generated (32+ characters)
- [ ] MySQL user has minimal necessary permissions
- [ ] HTTPS enabled on web server
- [ ] API key matches between server config.php and bot config.py
- [ ] Test health endpoint is accessible
- [ ] Test authenticated endpoint requires valid API key

---

## Troubleshooting

### 500 Internal Server Error
1. Check PHP error logs: `/var/log/apache2/error.log` or `/var/log/nginx/error.log`
2. Verify `config.php` exists and has correct MySQL credentials
3. Test MySQL connection: `php -r "new PDO('mysql:host=localhost', 'user', 'pass');"`
4. Ensure PHP extensions loaded: `php -m | grep -E 'pdo|mysql'`

### 401 Unauthorized
- API key mismatch between `config.php` and bot `config.py`
- Check header format: `Authorization: Bearer YOUR_KEY`

### Database Connection Failed
- Verify MySQL is running: `systemctl status mysql`
- Test connection: `mysql -u username -p`
- Check MySQL allows connections from localhost
- Verify credentials in `config.php`

### 404 Not Found
- Apache: Ensure `mod_rewrite` enabled: `a2enmod rewrite`
- Check `.htaccess` is present and readable
- Verify `AllowOverride All` in Apache config
- Nginx: Check location block configuration

---

## File Structure on Server

```
/path/to/webserver/twitch-gpt-chat-bot/api-server/
├── config.php              ← Your credentials (NOT in git)
├── config.example.php      ← Template
├── composer.json           ← Dependencies
├── vendor/                 ← Composer packages
├── public/
│   └── index.php           ← Main entry point
├── src/
│   ├── Database.php        ← MySQL adapter
│   ├── middleware/
│   │   └── AuthMiddleware.php
│   └── routes/
│       ├── players.php
│       └── replays.php
└── .htaccess               ← URL rewriting
```

---

## Maintenance

### Update API
```bash
cd /path/to/webserver/twitch-gpt-chat-bot
git pull
cd api-server
composer install --no-dev
```

### View Logs
- Check web server error logs for PHP errors
- API logs to web server error log (no separate log file)

### Backup
```bash
# Backup config (contains API key)
cp config.php config.php.backup

# MySQL backup
mysqldump -u user -p mathison > mathison_backup.sql
```

---

## Performance Tips

- Enable PHP OPcache for production
- Use connection pooling in PHP-FPM
- Consider adding rate limiting for API endpoints
- Monitor API response times in logs

---

## Next Steps

After deployment:
1. Test health endpoint from browser
2. Test authenticated endpoint with curl
3. Start bot in API mode on your PC
4. Play a game and verify bot queries work
5. Check bot logs for API request logging
6. Celebrate! 🎉

