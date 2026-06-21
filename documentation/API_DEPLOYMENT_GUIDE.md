# API Deployment Guide

This guide explains when you need to "start" the API servers and different deployment options.

## Understanding "Starting" the Server

### Short Answer
**Development**: You manually start with `php -S localhost:8000`  
**Production (Apache/Nginx)**: No manual start needed - web server handles it automatically

---

## Deployment Scenarios

### 1. Local Development (Manual Start Required)

When testing on your local machine:

```bash
# Mathison API (port 8000)
cd api-server
php -S localhost:8000 -t public

# PsiStorm API (port 8001)
cd api-psistorm
php -S localhost:8001 -t public
```

**Why manual start?**
- PHP's built-in server is for development only
- You explicitly start it when you want to test
- Stops when you close the terminal

**URLs**:
- `http://localhost:8000` - Mathison API
- `http://localhost:8001` - PsiStorm API

---

### 2. Production with Apache (No Manual Start)

When deployed to a web server with Apache:

**No "start" command needed!** Apache runs 24/7 and automatically handles PHP requests.

#### Setup
```bash
# Copy to web directory
cp -r api-server /var/www/html/api-server
cp -r api-psistorm /var/www/html/api-psistorm

# Configure
cd /var/www/html/api-server
composer install --no-dev
cp config.example.php config.php
nano config.php  # Edit settings

# Same for api-psistorm
cd /var/www/html/api-psistorm
composer install --no-dev
cp config.example.php config.php
nano config.php
```

#### Access
```
https://yourdomain.com/api-server/public/health
https://yourdomain.com/api-psistorm/public/health
```

**How it works**:
- Apache is already running as a service
- `.htaccess` files route requests to `index.php`
- PHP processes requests through Apache's `mod_php` or PHP-FPM
- Available 24/7 without manual intervention

---

### 3. Production with Nginx + PHP-FPM (No Manual Start)

Similar to Apache, Nginx runs continuously:

#### Nginx Config Example
```nginx
# /etc/nginx/sites-available/api-server
server {
    listen 80;
    server_name api.yourdomain.com;
    root /var/www/html/api-server/public;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
```

**Access**:
```
https://api.yourdomain.com/health
```

---

### 4. Shared Hosting (No Manual Start)

On shared hosting (GoDaddy, Bluehost, etc.):

1. Upload `api-server` or `api-psistorm` folder via FTP/cPanel
2. Place in `public_html` or subdirectory
3. Configure `config.php`
4. Access immediately - hosting provider's Apache/Nginx handles it

**Example structure**:
```
public_html/
  api-server/
    public/
      index.php
  api-psistorm/
    public/
      index.php
```

**URLs**:
```
https://yourdomain.com/api-server/public/health
https://yourdomain.com/api-psistorm/public/health
```

---

## Can You Copy/Paste the Folder?

### ✅ YES - Completely Portable!

Both `api-server` and `api-psistorm` folders are **self-contained** and can be:
- ✅ Copied to any project
- ✅ Copied to any server
- ✅ Run multiple instances with different configs
- ✅ Shared with other developers

### What You Need After Copying

```bash
# 1. Install dependencies
composer install

# 2. Create config
cp config.example.php config.php

# 3. Edit config.php
nano config.php  # Set database, API key, etc.
```

**That's it!** The folder is ready to use.

---

## Multiple Instances Example

You can run **multiple copies** pointing to different databases:

```
/var/www/html/
  api-mathison/         # Points to 'mathison' database
    config.php → database: 'mathison'
  
  api-psistorm/         # Points to 'psistorm' database
    config.php → database: 'psistorm'
  
  api-archive/          # Copy of api-psistorm, points to 'archive' database
    config.php → database: 'archive'
  
  api-test/             # Copy of api-psistorm, points to 'test' database
    config.php → database: 'test'
```

**URLs**:
```
https://yourdomain.com/api-mathison/public/health
https://yourdomain.com/api-psistorm/public/health
https://yourdomain.com/api-archive/public/health
https://yourdomain.com/api-test/public/health
```

**Each has its own**:
- Database connection
- API key
- Security settings
- Row limits
- Table exclusions

---

## Deployment Options Summary

| Method | Manual Start? | When to Use | Complexity |
|--------|--------------|-------------|------------|
| **PHP Built-in Server** | ✅ Yes | Local development/testing | Easy |
| **Apache (mod_php)** | ❌ No | Production, shared hosting | Easy |
| **Nginx + PHP-FPM** | ❌ No | Production, high traffic | Medium |
| **Docker** | ❌ No* | Containerized deployment | Medium |
| **Serverless** | ❌ No | AWS Lambda, etc. | Hard |

*Docker: You start the container once, not the PHP server

---

## Production Deployment Walkthrough

### Option A: Apache (Recommended for Simplicity)

```bash
# 1. Copy files
sudo cp -r api-psistorm /var/www/html/

# 2. Set ownership
sudo chown -R www-data:www-data /var/www/html/api-psistorm

# 3. Install dependencies
cd /var/www/html/api-psistorm
sudo -u www-data composer install --no-dev --optimize-autoloader

# 4. Configure
sudo cp config.example.php config.php
sudo nano config.php
# Set database, API key, base_path

# 5. Set permissions
sudo chmod 644 config.php
sudo chmod 755 public

# 6. Enable mod_rewrite (if not already)
sudo a2enmod rewrite
sudo systemctl restart apache2

# Done! Access at: https://yourdomain.com/api-psistorm/public/health
```

### Option B: Nginx + PHP-FPM

```bash
# 1. Copy files (same as Apache)
sudo cp -r api-psistorm /var/www/html/
sudo chown -R www-data:www-data /var/www/html/api-psistorm
cd /var/www/html/api-psistorm
sudo -u www-data composer install --no-dev --optimize-autoloader
sudo cp config.example.php config.php
sudo nano config.php

# 2. Create Nginx config
sudo nano /etc/nginx/sites-available/api-psistorm
```

**Nginx config**:
```nginx
server {
    listen 80;
    server_name api-psistorm.yourdomain.com;
    root /var/www/html/api-psistorm/public;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\.ht {
        deny all;
    }
}
```

```bash
# 3. Enable and restart
sudo ln -s /etc/nginx/sites-available/api-psistorm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Done! Access at: https://api-psistorm.yourdomain.com/health
```

### Option C: Docker (Portable Containers)

Create `api-psistorm/Dockerfile`:
```dockerfile
FROM php:8.1-apache

# Install dependencies
RUN apt-get update && apt-get install -y \
    libzip-dev \
    unzip \
    && docker-php-ext-install pdo pdo_mysql zip

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Copy application
COPY . /var/www/html
WORKDIR /var/www/html

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader

# Enable Apache modules
RUN a2enmod rewrite

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
```

Create `api-psistorm/docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8001:80"
    volumes:
      - ./config.php:/var/www/html/config.php
    environment:
      - APACHE_DOCUMENT_ROOT=/var/www/html/public
    restart: unless-stopped
```

**Deploy**:
```bash
cd api-psistorm
cp config.example.php config.php
nano config.php  # Configure

docker-compose up -d

# Access at: http://localhost:8001/health
```

---

## When Each API Needs to Be "Started"

### Development (Local Testing)
```bash
# Terminal 1: Mathison API
cd api-server
php -S localhost:8000 -t public

# Terminal 2: PsiStorm API
cd api-psistorm
php -S localhost:8001 -t public
```

**Both need manual start** for local testing.

### Production (Apache/Nginx)
```bash
# No manual start needed!
# Just copy files and configure
```

Apache/Nginx automatically handle both APIs.

---

## Current Setup on psistorm.com

Based on your existing setup:

```
https://psistorm.com/api-server/public/health  ← Mathison API
```

This suggests you're using **Apache in a subdirectory**. To add PsiStorm API:

```bash
# SSH into your server
ssh user@psistorm.com

# Copy api-psistorm folder
cd /var/www/html  # Or wherever api-server is located
cp -r ~/path/to/api-psistorm ./

# Configure
cd api-psistorm
composer install --no-dev
cp config.example.php config.php
nano config.php
# Set: $base_path = '/api-psistorm/public';
# Set database to 'psistorm'
# Set API key

# Set permissions
chmod 644 config.php

# Test
curl https://psistorm.com/api-psistorm/public/health
```

**No restart needed** - Apache will automatically serve it at:
```
https://psistorm.com/api-psistorm/public/health
https://psistorm.com/api-psistorm/public/api/v1/tables
```

---

## Portability Checklist

To use api-psistorm in another project:

### ✅ What to Copy
```
api-psistorm/
  ├── composer.json           ✅ Copy
  ├── config.example.php      ✅ Copy
  ├── .gitignore             ✅ Copy
  ├── public/                ✅ Copy (all files)
  ├── src/                   ✅ Copy (all files)
  └── README.md              ✅ Copy (optional)
```

### ❌ What NOT to Copy
```
api-psistorm/
  ├── config.php             ❌ DON'T copy (has your credentials)
  ├── vendor/                ❌ DON'T copy (regenerate with composer)
  └── composer.lock          ❌ DON'T copy (regenerate)
```

### After Copying
```bash
# In the new location
cd path/to/new/project/api-psistorm

# 1. Install dependencies
composer install

# 2. Create config
cp config.example.php config.php
nano config.php  # Edit for this project

# 3. Done!
```

---

## Summary

### Development
- **Manual start required**: `php -S localhost:8000 -t public`
- **Why**: PHP built-in server is temporary, for testing only
- **Both APIs**: Need separate terminals/ports

### Production (Apache/Nginx)
- **No manual start**: Web server runs 24/7
- **Why**: Apache/Nginx automatically handle PHP requests
- **Both APIs**: Work simultaneously, different URLs

### Portability
- **Fully portable**: Copy folder anywhere
- **After copying**: Run `composer install` and configure `config.php`
- **Multiple instances**: Each folder can point to different databases

### Your Situation
Since you have `https://psistorm.com/api-server/public/`, you're on **Apache in production**. Just copy `api-psistorm` to the same directory and configure - **no manual start needed**.
