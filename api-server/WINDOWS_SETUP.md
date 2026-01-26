# PHP Installation & Setup Guide for Windows

## Quick Install Instructions

### Step 1: Download PHP for Windows

1. Visit: https://windows.php.net/download/
2. Download the latest **PHP 8.3 VS16 x64 Thread Safe** ZIP file
3. Extract to: `C:\php` (or any location you prefer)

### Step 2: Add PHP to PATH (Optional but recommended)

1. Open System Environment Variables
2. Add `C:\php` to your PATH
3. Or just use full path when running commands

### Step 3: Verify Installation

Open PowerShell and run:
```powershell
C:\php\php.exe -v
```

You should see PHP version info.

### Step 4: Install Composer (PHP Package Manager)

1. Download from: https://getcomposer.org/Composer-Setup.exe
2. Run installer (it will find your PHP installation)
3. Or download composer.phar manually and place in `C:\php\`

### Step 5: Install API Dependencies

From the project root:
```powershell
cd api-server
C:\php\php.exe C:\php\composer.phar install
```

Or if Composer is in PATH:
```powershell
cd api-server
composer install
```

### Step 6: Configure the API

1. Copy the config example:
   ```powershell
   cd api-server
   copy config.example.php config.php
   ```

2. Edit `config.php` with your MySQL credentials:
   ```php
   <?php
   $db_config = [
       'host' => 'localhost',
       'user' => 'test',
       'password' => 'password',
       'database' => 'mathison'
   ];
   
   $api_key = 'your-secret-api-key-here';
   ```

### Step 7: Start the PHP Built-in Server

```powershell
# From project root
cd api-server\public
C:\php\php.exe -S localhost:8000

# Or use port 80 (requires admin):
C:\php\php.exe -S localhost:80
```

The server will run on: `http://localhost:8000`

### Step 8: Test the API

Open another PowerShell window:
```powershell
# Health check (no auth)
curl http://localhost:8000/health

# Authenticated endpoint
curl -H "Authorization: Bearer your-secret-api-key-here" http://localhost:8000/api/v1/replays/last
```

### Step 9: Configure Python Bot to Use API

Edit `settings/config.py`:
```python
DB_MODE = "api"
DB_API_URL = "http://localhost:8000"
DB_API_KEY = "your-secret-api-key-here"
```

---

## Alternative: Using Port 8080 or Other Ports

If port 80 or 8000 are taken, use any port:

```powershell
# Use port 8080
C:\php\php.exe -S localhost:8080

# Use port 3000
C:\php\php.exe -S localhost:3000
```

Then update `settings/config.py`:
```python
DB_API_URL = "http://localhost:8080"  # or whatever port you chose
```

---

## Quick Commands (After Setup)

**Start API Server:**
```powershell
cd C:\Users\karl_\Downloads\CODE\twitch-gpt-chat-bot\api-server\public
C:\php\php.exe -S localhost:8000
```

**Run PHP Tests:**
```powershell
cd C:\Users\karl_\Downloads\CODE\twitch-gpt-chat-bot\api-server
C:\php\php.exe vendor\bin\phpunit tests/api_test.php
```

**Run Python Tests:**
```powershell
cd C:\Users\karl_\Downloads\CODE\twitch-gpt-chat-bot
python tests/adapters/test_api_database_client.py
```

---

## Troubleshooting

**"php is not recognized"**
- Use full path: `C:\php\php.exe` instead of just `php`
- Or add `C:\php` to your PATH

**"composer is not recognized"**
- Use: `C:\php\php.exe C:\php\composer.phar` instead of `composer`

**"Address already in use"**
- Port 80/8000 is taken, use different port: `php -S localhost:8080`

**"Class 'PDO' not found"**
- Enable PDO in `php.ini`: uncomment `extension=pdo_mysql`

