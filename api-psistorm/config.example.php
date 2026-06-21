<?php
/**
 * PsiStorm Database API Configuration Template
 * 
 * INSTRUCTIONS:
 * 1. Copy this file to config.php
 * 2. Fill in your MySQL credentials
 * 3. Generate a secure random API key
 * 4. Keep config.php secure (it's gitignored)
 */

// MySQL Database Configuration
$db_config = [
    'host'     => 'localhost',           // MySQL host
    'user'     => 'your_mysql_user',     // MySQL username
    'password' => 'your_mysql_password', // MySQL password
    'database' => 'psistorm',            // Database name
    'charset'  => 'utf8mb4'              // Character set
];

// API Security - Generate a secure random key
// Example: openssl rand -base64 32
$api_key = 'CHANGE-THIS-TO-A-SECURE-RANDOM-KEY';

// Base path when app is in a subpath. '' for local dev.
// When URL is https://psistorm.com/api-psistorm/public/health, set to '/api-psistorm/public':
$base_path = '';

// Query Restrictions (optional security)
// Set to true to allow only SELECT queries (read-only mode)
$read_only_mode = false;

// Maximum rows returned per query (prevents massive data dumps)
$max_rows_per_query = 1000;

// Tables to exclude from API access (sensitive tables)
$excluded_tables = [
    // 'passwords',
    // 'api_keys',
    // 'sensitive_data'
];
