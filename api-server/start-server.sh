#!/bin/bash
# Quick start script for PHP API server on Linux/Mac

echo ""
echo "===================================="
echo " Mathison Database API - Unix"
echo "===================================="
echo ""

# Check if PHP is installed
if ! command -v php &> /dev/null; then
    echo "ERROR: PHP not found!"
    echo "Please install PHP 8.0 or higher"
    exit 1
fi

echo "Using PHP: $(which php)"
php -v | head -n 1

# Check if config.php exists
if [ ! -f "$(dirname "$0")/config.php" ]; then
    echo ""
    echo "WARNING: config.php not found!"
    echo "Please copy config.example.php to config.php and configure it"
    echo ""
    echo "Running: cp config.example.php config.php"
    cp "$(dirname "$0")/config.example.php" "$(dirname "$0")/config.php"
    echo ""
    echo "Please edit api-server/config.php with your database credentials"
    read -p "Press Enter to continue..."
fi

# Check if vendor directory exists
if [ ! -d "$(dirname "$0")/vendor" ]; then
    echo ""
    echo "ERROR: Dependencies not installed!"
    echo "Please run: composer install"
    echo ""
    exit 1
fi

# Default port
PORT=8000

# Check if port argument was provided
if [ ! -z "$1" ]; then
    PORT=$1
fi

echo ""
echo "Starting PHP Development Server..."
echo "URL: http://localhost:$PORT"
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")/public"
php -S localhost:$PORT

