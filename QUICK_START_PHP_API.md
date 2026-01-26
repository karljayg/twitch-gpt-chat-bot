# Quick Start: Test Database API on Windows

## TL;DR - Fast Setup

### 1. Install PHP (5 minutes)

Download: https://windows.php.net/download/
- Get **PHP 8.3 VS16 x64 Thread Safe ZIP**
- Extract to `C:\php`

### 2. Install Composer

Download & run: https://getcomposer.org/Composer-Setup.exe

### 3. Setup API (from project root)

```powershell
cd api-server

# Copy config
copy config.example.php config.php

# Edit config.php - set your MySQL credentials

# Install dependencies
composer install
```

### 4. Start Server

```powershell
# Easy way:
.\start-server.bat

# Or manually:
cd public
php -S localhost:8000
```

### 5. Configure Bot to Use API

Edit `settings\config.py`:
```python
DB_MODE = "api"
DB_API_URL = "http://localhost:8000"
DB_API_KEY = "your-secret-api-key-here"  # Must match config.php
```

### 6. Test

```powershell
# Test API health
curl http://localhost:8000/health

# Test bot
python run_core.py
```

---

## Port Configuration

**Yes, port is configurable!**

### Change API Server Port:

```powershell
# Start on different port
cd api-server
.\start-server.bat 8080

# Or manually
cd public
php -S localhost:8080
```

### Update Bot Config:

```python
# settings/config.py
DB_API_URL = "http://localhost:8080"  # Match your port
```

### Common Ports:

- `80` - Standard HTTP (requires admin on Windows)
- `8000` - Default in our scripts
- `8080` - Common alternative
- `3000` - Another common dev port

---

## Full Setup Documentation

See `api-server/WINDOWS_SETUP.md` for detailed instructions.

