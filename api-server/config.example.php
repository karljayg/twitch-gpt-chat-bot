<?php
/**
 * Mathison Database API Configuration Template
 * 
 * INSTRUCTIONS:
 * 1. Copy this file to config.php
 * 2. Fill in your MySQL credentials
 * 3. Generate a secure random API key
 * 4. Keep config.php secure (it's gitignored)
 */

// MySQL Database Configuration
$db_config = [
    'host'     => 'localhost',           // MySQL host (usually localhost)
    'user'     => 'your_mysql_user',     // MySQL username
    'password' => 'your_mysql_password', // MySQL password
    'database' => 'mathison',            // Database name
    'charset'  => 'utf8mb4'              // Character set
];

// Optional: psistorm database for read-only FSL endpoints under /api/v1/fsl/*
// Omit this variable or leave 'database' empty to disable FSL routes (503).
$psistorm_db_config = [
    'host'     => 'localhost',
    'user'     => 'your_psistorm_mysql_user',
    'password' => 'your_psistorm_mysql_password',
    'database' => 'psistorm',
    'charset'  => 'utf8mb4',
];

// API Security - Generate a secure random key
// Example: openssl rand -base64 32
$api_key = 'CHANGE-THIS-TO-A-SECURE-RANDOM-KEY';

// Base path when app is in a subpath. '' for local (php -S localhost:8000 -t public).
// When URL is https://psistorm.com/api-server/public/health, set to '/api-server/public':
$base_path = '';

// Note: This same API key must be set in the bot's config.py as DB_API_KEY

