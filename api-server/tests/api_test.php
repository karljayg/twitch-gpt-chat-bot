<?php
/**
 * API Test Suite
 * 
 * Tests all API endpoints to verify functionality.
 * Run: php tests/api_test.php
 * 
 * Usage:
 *   php tests/api_test.php [base_url] [api_key]
 * 
 * Example:
 *   php tests/api_test.php http://localhost:8000 test-api-key-123
 */

// Configuration
$base_url = $argv[1] ?? 'http://localhost:8000';
$api_key = $argv[2] ?? 'test-api-key';

// Colors for output
$GREEN = "\033[0;32m";
$RED = "\033[0;31m";
$YELLOW = "\033[1;33m";
$NC = "\033[0m"; // No Color

// Test counters
$passed = 0;
$failed = 0;
$total = 0;

function test($name, $callback) {
    global $passed, $failed, $total, $GREEN, $RED, $NC;
    $total++;
    
    echo "\nTest #{$total}: {$name}\n";
    
    try {
        $result = $callback();
        if ($result === true) {
            $passed++;
            echo "{$GREEN}✓ PASS{$NC}\n";
        } else {
            $failed++;
            echo "{$RED}✗ FAIL: {$result}{$NC}\n";
        }
    } catch (Exception $e) {
        $failed++;
        echo "{$RED}✗ EXCEPTION: {$e->getMessage()}{$NC}\n";
    }
}

function api_request($url, $api_key = null) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    
    if ($api_key !== null) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            "Authorization: Bearer {$api_key}"
        ]);
    }
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    return [
        'code' => $http_code,
        'body' => $response,
        'json' => json_decode($response, true)
    ];
}

echo "\n========================================\n";
echo "Mathison API Test Suite\n";
echo "========================================\n";
echo "Base URL: {$base_url}\n";
echo "API Key: " . substr($api_key, 0, 10) . "...\n";
echo "========================================\n";

// ===== Health Check =====

test("Health check (no auth required)", function() use ($base_url) {
    $response = api_request("{$base_url}/health");
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    if (!isset($response['json']['status']) || $response['json']['status'] !== 'healthy') {
        return "Expected status=healthy, got: " . print_r($response['json'], true);
    }
    
    if (!isset($response['json']['database'])) {
        return "Missing database status";
    }
    
    return true;
});

// ===== Authentication Tests =====

test("Auth: Reject request without API key", function() use ($base_url) {
    $response = api_request("{$base_url}/api/v1/replays/last");
    
    if ($response['code'] !== 401) {
        return "Expected 401 Unauthorized, got {$response['code']}";
    }
    
    if (!isset($response['json']['error'])) {
        return "Expected error message in response";
    }
    
    return true;
});

test("Auth: Reject request with invalid API key", function() use ($base_url) {
    $response = api_request("{$base_url}/api/v1/replays/last", "invalid-key");
    
    if ($response['code'] !== 401) {
        return "Expected 401 Unauthorized, got {$response['code']}";
    }
    
    return true;
});

test("Auth: Accept request with valid API key", function() use ($base_url, $api_key) {
    $response = api_request("{$base_url}/api/v1/replays/last", $api_key);
    
    // Should not be 401 or 403
    if ($response['code'] === 401 || $response['code'] === 403) {
        return "API key rejected (wrong key?)";
    }
    
    return true;
});

// ===== Player Endpoints =====

test("Players: Check player and race exists", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/check?player_name=TestPlayer&player_race=Protoss",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    // Response can be null or array, both are valid
    $data = $response['json'];
    if ($data !== null && !is_array($data)) {
        return "Expected null or array, got: " . gettype($data);
    }
    
    return true;
});

test("Players: Missing parameters returns 400", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/check?player_name=TestPlayer",
        $api_key
    );
    
    if ($response['code'] !== 400) {
        return "Expected 400 Bad Request, got {$response['code']}";
    }
    
    if (!isset($response['json']['error'])) {
        return "Expected error message";
    }
    
    return true;
});

test("Players: Check if player exists", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/TestPlayer/exists",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    if (!isset($response['json']['exists'])) {
        return "Missing 'exists' field in response";
    }
    
    if (!is_bool($response['json']['exists'])) {
        return "'exists' should be boolean";
    }
    
    return true;
});

test("Players: Get player records", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/TestPlayer/records",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    if (!is_array($response['json'])) {
        return "Expected array response";
    }
    
    return true;
});

test("Players: Get player comments", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/TestPlayer/comments?race=Protoss",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    if (!is_array($response['json'])) {
        return "Expected array response";
    }
    
    return true;
});

test("Players: Get overall records", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/players/TestPlayer/overall_records",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    if (!isset($response['json']['records'])) {
        return "Missing 'records' field";
    }
    
    return true;
});

// ===== Replay Endpoints =====

test("Replays: Get last replay", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/replays/last",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    // Can be null if no replays, or array with data
    $data = $response['json'];
    if ($data !== null && !is_array($data)) {
        return "Expected null or array";
    }
    
    return true;
});

test("Replays: Get specific replay (non-existent)", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/replays/999999",
        $api_key
    );
    
    if ($response['code'] !== 404) {
        return "Expected 404 for non-existent replay, got {$response['code']}";
    }
    
    return true;
});

// ===== Build Order Endpoints =====

test("Build Orders: Extract opponent build order", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/build_orders/extract?opponent_name=TestPlayer&opponent_race=Protoss&streamer_race=Terran",
        $api_key
    );
    
    if ($response['code'] !== 200) {
        return "Expected 200, got {$response['code']}";
    }
    
    // Can be null if not found, or array with build order
    $data = $response['json'];
    if ($data !== null && !is_array($data)) {
        return "Expected null or array";
    }
    
    return true;
});

test("Build Orders: Missing parameters returns 400", function() use ($base_url, $api_key) {
    $response = api_request(
        "{$base_url}/api/v1/build_orders/extract?opponent_name=TestPlayer",
        $api_key
    );
    
    if ($response['code'] !== 400) {
        return "Expected 400 Bad Request, got {$response['code']}";
    }
    
    return true;
});

// ===== Summary =====

echo "\n========================================\n";
echo "Test Results\n";
echo "========================================\n";
echo "Total:  {$total}\n";
echo "{$GREEN}Passed: {$passed}{$NC}\n";
if ($failed > 0) {
    echo "{$RED}Failed: {$failed}{$NC}\n";
} else {
    echo "Failed: {$failed}\n";
}
echo "========================================\n";

if ($failed > 0) {
    exit(1);
} else {
    echo "{$GREEN}All tests passed!{$NC}\n";
    exit(0);
}

