<?php
namespace Mathison\API;

use PDO;
use PDOException;
use Exception;

class Database {
    private $conn;
    private $config;
    
    public function __construct($config) {
        $this->config = $config;
        $this->connect();
    }
    
    private function connect() {
        $dsn = "mysql:host={$this->config['host']};dbname={$this->config['database']};charset={$this->config['charset']}";
        
        try {
            $this->conn = new PDO($dsn, $this->config['user'], $this->config['password'], [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
            ]);
        } catch (PDOException $e) {
            throw new Exception("Database connection failed: " . $e->getMessage());
        }
    }
    
    public function isConnected() {
        try {
            return $this->conn !== null && $this->conn->query('SELECT 1')->fetchColumn() === 1;
        } catch (Exception $e) {
            return false;
        }
    }
    
    // ===== Player Methods =====
    
    public function checkPlayerAndRaceExists($player_name, $player_race) {
        $sql = "
            SELECT r.*, 
                   p1.SC2_UserId AS Player1_Name,
                   p2.SC2_UserId AS Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE ((p1.SC2_UserId = ? AND r.Player1_Race = ?)
                OR (p2.SC2_UserId = ? AND r.Player2_Race = ?))
            ORDER BY (r.Player_Comments IS NOT NULL AND r.Player_Comments != '') DESC,
                     r.Date_Played DESC
            LIMIT 1
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name, $player_race, $player_name, $player_race]);
        $result = $stmt->fetch();
        return $result ?: null;
    }
    
    public function checkPlayerExists($player_name) {
        $sql = "SELECT * FROM Players WHERE SC2_UserId = ? LIMIT 1";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name]);
        $result = $stmt->fetch();
        return $result ?: null;
    }
    
    public function getPlayerRecords($player_name) {
        $sql = "
            SELECT 
                CONCAT(p1.SC2_UserId, ', ', p2.SC2_UserId, ', ',
                       COALESCE(SUM(CASE WHEN r.Player1_Result = 'Win' THEN 1 ELSE 0 END), 0), ' wins, ',
                       COALESCE(SUM(CASE WHEN r.Player1_Result = 'Lose' THEN 1 ELSE 0 END), 0), ' losses') as record
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE p1.SC2_UserId = ?
            GROUP BY p1.SC2_UserId, p2.SC2_UserId
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name]);
        return $stmt->fetchAll(PDO::FETCH_COLUMN);
    }
    
    public function getPlayerComments($player_name, $player_race) {
        $sql = "
            SELECT 
                r.Player_Comments,
                r.Map,
                r.Date_Played,
                r.GameDuration
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE ((p1.SC2_UserId = ? AND r.Player1_Race = ?)
                OR (p2.SC2_UserId = ? AND r.Player2_Race = ?))
                AND r.Player_Comments IS NOT NULL
                AND TRIM(r.Player_Comments) <> ''
            ORDER BY r.Date_Played DESC
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name, $player_race, $player_name, $player_race]);
        
        $results = [];
        foreach ($stmt->fetchAll() as $row) {
            $results[] = [
                'player_comments' => $row['Player_Comments'],
                'map' => $row['Map'],
                'date_played' => $row['Date_Played'],
                'game_duration' => $row['GameDuration']
            ];
        }
        return $results;
    }
    
    public function getPlayerOverallRecords($player_name) {
        $sql = "
            SELECT 
                p.SC2_UserId AS Player,
                SUM(CASE WHEN (r.Player1_Id = p.Id AND r.Player1_Result = 'Win') OR 
                              (r.Player2_Id = p.Id AND r.Player2_Result = 'Win') THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (r.Player1_Id = p.Id AND r.Player1_Result = 'Lose') OR 
                              (r.Player2_Id = p.Id AND r.Player2_Result = 'Lose') THEN 1 ELSE 0 END) AS Losses
            FROM Replays r
            JOIN Players p ON r.Player1_Id = p.Id OR r.Player2_Id = p.Id
            WHERE p.SC2_UserId = ? AND r.GameType = '1v1'
            GROUP BY p.SC2_UserId
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name]);
        $result = $stmt->fetch();
        
        if ($result) {
            return "Overall matchup records for {$player_name}: \n{$result['Wins']} wins - {$result['Losses']} losses\n";
        }
        return "No records found for {$player_name}";
    }
    
    // ===== Replay Methods =====
    
    public function getLastReplayInfo() {
        $sql = "SELECT * FROM Replays ORDER BY Date_Played DESC LIMIT 1";
        $stmt = $this->conn->query($sql);
        $result = $stmt->fetch();
        return $result ?: null;
    }
    
    public function getLatestReplay() {
        // Get latest replay with player names (matches Python get_latest_replay)
        $sql = "
            SELECT r.ReplayId, r.UnixTimestamp, r.Player1_Id, r.Player2_Id, 
                   r.Player1_Result, r.Player2_Result,
                   r.Map, r.GameDuration, r.Date_Played, r.Player_Comments,
                   p1.SC2_UserId as Player1_Name, p2.SC2_UserId as Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE r.UnixTimestamp = (SELECT MAX(UnixTimestamp) FROM Replays)
        ";
        $stmt = $this->conn->query($sql);
        $result = $stmt->fetch();
        
        if (!$result) {
            return null;
        }
        
        // Return raw data - client will determine opponent based on streamer accounts
        // Format matches Python implementation
        $date_played = is_string($result['Date_Played']) ? $result['Date_Played'] : $result['Date_Played']->format('Y-m-d H:i:s');
        
        return [
            'ReplayId' => $result['ReplayId'],
            'Player1_Name' => $result['Player1_Name'],
            'Player2_Name' => $result['Player2_Name'],
            'Player1_Result' => $result['Player1_Result'],
            'Player2_Result' => $result['Player2_Result'],
            'map' => $result['Map'],
            'date' => $date_played,
            'duration' => $result['GameDuration'],
            'timestamp' => $result['UnixTimestamp'],
            'existing_comment' => $result['Player_Comments']
        ];
    }

    public function getReplayByRecencyOffset($offset) {
        $offset = max(0, (int)$offset);
        $sql = "
            SELECT r.*, 
                   p1.SC2_UserId AS Player1_Name, 
                   p2.SC2_UserId AS Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            ORDER BY r.UnixTimestamp DESC
            LIMIT 1 OFFSET ?
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$offset]);
        $result = $stmt->fetch();
        return $result ?: null;
    }
    
    public function getGamesForLastXHours($hours) {
        $end_date = date('Y-m-d H:i:s');
        $start_date = date('Y-m-d H:i:s', strtotime("-{$hours} hours"));
        
        $sql = "
            SELECT 
                CONCAT(p1.SC2_UserId, ' vs ', p2.SC2_UserId) AS Players,
                CASE
                    WHEN r.Player1_Result = 'Win' THEN p1.SC2_UserId
                    WHEN r.Player2_Result = 'Win' THEN p2.SC2_UserId
                    ELSE 'Draw'
                END AS Winner,
                r.Map,
                r.Date_Played
            FROM 
                Replays r
            JOIN 
                Players p1 ON r.Player1_Id = p1.Id
            JOIN 
                Players p2 ON r.Player2_Id = p2.Id
            WHERE 
                r.Date_Played >= ? AND r.Date_Played <= ?
            ORDER BY 
                r.Date_Played DESC
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$start_date, $end_date]);
        $results = $stmt->fetchAll();
        
        $formatted_results = [];
        foreach ($results as $row) {
            $date_played = is_string($row['Date_Played']) ? $row['Date_Played'] : $row['Date_Played']->format('Y-m-d H:i:s');
            $formatted_results[] = "{$row['Players']} on {$row['Map']}, Winner: {$row['Winner']}, Played at: {$date_played}";
        }
        
        return $formatted_results;
    }
    
    public function getHeadToHeadMatchup($player1, $player2) {
        // Subquery version - works with both ONLY_FULL_GROUP_BY enabled and disabled
        // Compatible with local (lenient) and remote (strict) MySQL configurations
        $sql = "
            SELECT 
                Player1_Race,
                Player2_Race,
                SUM(Player1_Wins) AS Player1_Wins,
                SUM(Player2_Wins) AS Player2_Wins
            FROM (
                SELECT 
                    CASE 
                        WHEN LOWER(p1.SC2_UserId) = LOWER(?) THEN r.Player1_Race
                        ELSE r.Player2_Race
                    END AS Player1_Race,
                    CASE 
                        WHEN LOWER(p1.SC2_UserId) = LOWER(?) THEN r.Player2_Race
                        ELSE r.Player1_Race
                    END AS Player2_Race,
                    CASE 
                        WHEN (LOWER(p1.SC2_UserId) = LOWER(?) AND r.Player1_Result = 'Win') OR 
                             (LOWER(p2.SC2_UserId) = LOWER(?) AND r.Player2_Result = 'Win') THEN 1 
                        ELSE 0 
                    END AS Player1_Wins,
                    CASE 
                        WHEN (LOWER(p1.SC2_UserId) = LOWER(?) AND r.Player1_Result = 'Win') OR 
                             (LOWER(p2.SC2_UserId) = LOWER(?) AND r.Player2_Result = 'Win') THEN 1 
                        ELSE 0 
                    END AS Player2_Wins
                FROM 
                    Replays r
                JOIN 
                    Players p1 ON r.Player1_Id = p1.Id
                JOIN 
                    Players p2 ON r.Player2_Id = p2.Id
                WHERE 
                    ((LOWER(p1.SC2_UserId) = LOWER(?) AND LOWER(p2.SC2_UserId) = LOWER(?)) OR 
                    (LOWER(p1.SC2_UserId) = LOWER(?) AND LOWER(p2.SC2_UserId) = LOWER(?)))
                    AND r.GameType = '1v1'
            ) AS subquery
            GROUP BY 
                Player1_Race,
                Player2_Race
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([
            $player1, $player1, $player1, $player1, $player2, $player2,
            $player1, $player2, $player2, $player1
        ]);
        $results = $stmt->fetchAll();
        
        $formatted_results = [];
        foreach ($results as $row) {
            $formatted_results[] = "{$player1} ({$row['Player1_Race']}) vs {$player2} ({$row['Player2_Race']}), {$row['Player1_Wins']} wins - {$row['Player2_Wins']} wins";
        }
        
        return $formatted_results;
    }
    
    public function getPlayerRaceMatchupRecords($player_name) {
        $sql = "
            SELECT 
                ? AS Player,
                Player_Race,
                Opponent_Race,
                SUM(Wins) AS Total_Wins,
                SUM(Losses) AS Total_Losses
            FROM
                (
                    SELECT 
                        r.Player1_Race AS Player_Race,
                        r.Player2_Race AS Opponent_Race,
                        SUM(CASE WHEN (r.Player1_Id = (SELECT Id FROM Players WHERE SC2_UserId = ?) AND r.Player1_Result = 'Win') THEN 1 ELSE 0 END) AS Wins,
                        SUM(CASE WHEN (r.Player1_Id = (SELECT Id FROM Players WHERE SC2_UserId = ?) AND r.Player1_Result = 'Lose') THEN 1 ELSE 0 END) AS Losses
                    FROM 
                        Replays r
                    WHERE 
                        EXISTS (SELECT 1 FROM Players WHERE SC2_UserId = ? AND Id = r.Player1_Id)
                        AND r.GameType = '1v1'
                    GROUP BY 
                        Player_Race, Opponent_Race
                    UNION ALL
                    SELECT 
                        r.Player2_Race AS Player_Race,
                        r.Player1_Race AS Opponent_Race,
                        SUM(CASE WHEN (r.Player2_Id = (SELECT Id FROM Players WHERE SC2_UserId = ?) AND r.Player2_Result = 'Win') THEN 1 ELSE 0 END) AS Wins,
                        SUM(CASE WHEN (r.Player2_Id = (SELECT Id FROM Players WHERE SC2_UserId = ?) AND r.Player2_Result = 'Lose') THEN 1 ELSE 0 END) AS Losses
                    FROM 
                        Replays r
                    WHERE 
                        EXISTS (SELECT 1 FROM Players WHERE SC2_UserId = ? AND Id = r.Player2_Id)
                        AND r.GameType = '1v1'
                    GROUP BY 
                        Player_Race, Opponent_Race
                ) AS CombinedResults
            GROUP BY 
                Player_Race, Opponent_Race
            ORDER BY 
                Player_Race, Opponent_Race
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player_name, $player_name, $player_name, $player_name, $player_name, $player_name, $player_name]);
        $results = $stmt->fetchAll();
        
        $output_string = "Race matchup records for {$player_name}: \n";
        foreach ($results as $row) {
            $output_string .= "{$row['Player_Race']} vs {$row['Opponent_Race']}: {$row['Total_Wins']} wins - {$row['Total_Losses']} losses\n";
        }
        
        return $output_string;
    }
    
    public function getReplayById($replay_id) {
        // Prefer SC2 ReplayId (external id used by chat commands).
        // Some deployments may not have Replays.Id; avoid hard failing on schema differences.
        $sqlReplayId = "
            SELECT r.*, 
                   p1.SC2_UserId AS Player1_Name, 
                   p2.SC2_UserId AS Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE r.ReplayId = ?
            ORDER BY r.Date_Played DESC
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sqlReplayId);
        $stmt->execute([$replay_id]);
        $result = $stmt->fetch();
        if ($result) {
            return $result;
        }

        // Optional backward compatibility: if internal Id exists, allow fallback.
        try {
            $sqlId = "
                SELECT r.*, 
                       p1.SC2_UserId AS Player1_Name, 
                       p2.SC2_UserId AS Player2_Name
                FROM Replays r
                JOIN Players p1 ON r.Player1_Id = p1.Id
                JOIN Players p2 ON r.Player2_Id = p2.Id
                WHERE r.Id = ?
                ORDER BY r.Date_Played DESC
                LIMIT 1
            ";
            $stmt2 = $this->conn->prepare($sqlId);
            $stmt2->execute([$replay_id]);
            $result2 = $stmt2->fetch();
            return $result2 ?: null;
        } catch (Exception $e) {
            // If Id column doesn't exist in this schema, just treat as not found.
            return null;
        }
    }
    
    public function extractOpponentBuildOrder($opponent_name, $opp_race, $streamer_picked_race) {
        $sql = "
            SELECT r.Replay_Summary
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE ((p1.SC2_UserId = ? AND r.Player2_PickRace = ?) OR (p2.SC2_UserId = ? AND r.Player1_PickRace = ?)) 
            AND ((p1.SC2_UserId = ? AND r.Player1_Race = ?) OR (p2.SC2_UserId = ? AND r.Player2_Race = ?))
            ORDER BY r.Date_Played DESC
            LIMIT 1
        ";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([
            $opponent_name, $streamer_picked_race, 
            $opponent_name, $streamer_picked_race, 
            $opponent_name, $opp_race, 
            $opponent_name, $opp_race
        ]);
        $row = $stmt->fetch();
        
        if ($row && !empty($row['Replay_Summary'])) {
            $replay_summary = $row['Replay_Summary'];
            
            // Find opponent's build order section
            $pattern = "/{$opponent_name}'s Build Order/i";
            if (preg_match($pattern, $replay_summary, $matches, PREG_OFFSET_CAPTURE)) {
                $build_order_start = $matches[0][1];
                $build_order_section = substr($replay_summary, $build_order_start);
                $build_order_lines = explode("\n", $build_order_section);
                
                $stripped_list = [];
                foreach ($build_order_lines as $line) {
                    $parts = explode(',', $line, 2);
                    if (count($parts) > 1) {
                        $stripped_list[] = trim($parts[1]);
                    } else {
                        $stripped_list[] = $parts[0];
                    }
                }
                
                $reformatted_list = [];
                foreach ($stripped_list as $line) {
                    if (preg_match('/Name: (\w+), Supply: (\d+)/', $line, $match)) {
                        $reformatted_list[] = "{$match[1]} at {$match[2]}";
                    } else {
                        $reformatted_list[] = $line;
                    }
                }
                
                // Remove quotes
                $reformatted_list = array_map(function($item) {
                    return str_replace(['"', "'"], '', $item);
                }, $reformatted_list);
                
                // Return first N steps (would need config value here)
                return array_slice($reformatted_list, 1, 120);
            }
        }
        
        return null;
    }
    
    public function updatePlayerCommentsInLastReplay($comment) {
        // Fetch the latest replay data
        $sql = "
            SELECT r.UnixTimestamp, r.ReplayId, r.Player1_Id, r.Player2_Id,
                   r.Player1_Race, r.Player2_Race, r.Player1_Result, r.Player2_Result,
                   r.Map, r.Date_Played, r.GameDuration, r.Replay_Summary,
                   p1.SC2_UserId as Player1_Name, p2.SC2_UserId as Player2_Name
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE r.UnixTimestamp = (SELECT MAX(UnixTimestamp) FROM Replays)
        ";
        $stmt = $this->conn->query($sql);
        $replay = $stmt->fetch();
        
        if (!$replay) {
            throw new Exception("No recent replays found to update.");
        }
        
        $latest_timestamp = $replay['UnixTimestamp'];
        
        // Update the Replays.Player_Comments column
        $sql = "UPDATE Replays SET Player_Comments = ? WHERE UnixTimestamp = ?";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$comment, $latest_timestamp]);
        
        // Also insert/update PlayerComments table (structured JSON data)
        // Determine opponent (assumes streamer is Player1 or Player2 - you may need to adjust this logic)
        $opponent_name = $replay['Player2_Name'];  // Default - adjust based on your streamer detection
        $opponent_race = $replay['Player2_Race'];
        $result = $replay['Player1_Result'];  // Default - adjust based on streamer
        
        // Generate comment_id from timestamp
        $comment_id = "comment_" . $latest_timestamp;
        
        // Check if comment already exists for this replay
        $check_sql = "SELECT comment_id FROM PlayerComments WHERE comment_id = ?";
        $check_stmt = $this->conn->prepare($check_sql);
        $check_stmt->execute([$comment_id]);
        $existing = $check_stmt->fetch();
        
        // Prepare JSON fields (empty arrays for now - pattern learning can update later)
        $keywords_json = json_encode([]);
        $build_order_json = json_encode([]);
        
        if ($existing) {
            // Update existing record
            $update_sql = "
                UPDATE PlayerComments 
                SET raw_comment = ?, 
                    cleaned_comment = ?,
                    opponent_name = ?,
                    opponent_race = ?,
                    result = ?,
                    map_name = ?,
                    duration = ?,
                    date_played = ?
                WHERE comment_id = ?
            ";
            $update_stmt = $this->conn->prepare($update_sql);
            $update_stmt->execute([
                $comment,
                $comment,  // cleaned_comment same as raw for now
                $opponent_name,
                $opponent_race,
                $result,
                $replay['Map'],
                $replay['GameDuration'],
                $replay['Date_Played'],
                $comment_id
            ]);
        } else {
            // Insert new record
            $insert_sql = "
                INSERT INTO PlayerComments 
                (comment_id, raw_comment, cleaned_comment, keywords, opponent_name, 
                 opponent_race, result, map_name, duration, date_played, build_order, pattern_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ";
            $insert_stmt = $this->conn->prepare($insert_sql);
            $insert_stmt->execute([
                $comment_id,
                $comment,
                $comment,  // cleaned_comment same as raw for now
                $keywords_json,
                $opponent_name,
                $opponent_race,
                $result,
                $replay['Map'],
                $replay['GameDuration'],
                $replay['Date_Played'],
                $build_order_json
            ]);
        }
        
        return ['success' => true, 'timestamp' => $latest_timestamp, 'comment_id' => $comment_id];
    }

    public function updatePlayerCommentsByReplayId($replay_id, $comment) {
        $sql = "UPDATE Replays SET Player_Comments = ? WHERE ReplayId = ?";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$comment, $replay_id]);
        return ['success' => $stmt->rowCount() > 0, 'replay_id' => (int)$replay_id];
    }
    
    public function savePlayerCommentWithData($comment_data) {
        // Save full comment data to PlayerComments table with keywords, build_order, etc.
        // comment_data should be a JSON string or array containing: raw_comment, cleaned_comment, keywords, game_data, etc.
        
        if (is_string($comment_data)) {
            $comment_data = json_decode($comment_data, true);
        }
        
        $raw_comment = $comment_data['raw_comment'] ?? $comment_data['comment'] ?? '';
        $cleaned_comment = $comment_data['cleaned_comment'] ?? $raw_comment;
        $keywords = $comment_data['keywords'] ?? [];
        $game_data = $comment_data['game_data'] ?? [];
        
        // Get replay info to link comment
        $sql = "SELECT MAX(UnixTimestamp) AS latest_timestamp FROM Replays";
        $stmt = $this->conn->query($sql);
        $result = $stmt->fetch();
        $latest_timestamp = $result['latest_timestamp'] ?? null;
        
        if (!$latest_timestamp) {
            throw new Exception("No recent replays found to link comment.");
        }
        
        $comment_id = "comment_" . $latest_timestamp;
        $keywords_json = json_encode($keywords);
        $build_order_json = json_encode($game_data['build_order'] ?? []);
        
        $opponent_name = $game_data['opponent_name'] ?? '';
        $opponent_race = $game_data['opponent_race'] ?? '';
        $result = $game_data['result'] ?? '';
        $map_name = $game_data['map'] ?? '';
        $duration = $game_data['duration'] ?? '';
        $date_played = $game_data['date'] ?? '';
        
        // Parse date if provided
        $date_played_sql = null;
        if ($date_played) {
            try {
                $date_played_sql = date('Y-m-d H:i:s', strtotime($date_played));
            } catch (Exception $e) {
                $date_played_sql = null;
            }
        }
        
        // Check if comment already exists
        $check_sql = "SELECT comment_id FROM PlayerComments WHERE comment_id = ?";
        $check_stmt = $this->conn->prepare($check_sql);
        $check_stmt->execute([$comment_id]);
        $existing = $check_stmt->fetch();
        
        if ($existing) {
            // Update existing record with full data
            $update_sql = "
                UPDATE PlayerComments 
                SET raw_comment = ?, 
                    cleaned_comment = ?,
                    keywords = ?,
                    opponent_name = ?,
                    opponent_race = ?,
                    result = ?,
                    map_name = ?,
                    duration = ?,
                    date_played = ?,
                    build_order = ?
                WHERE comment_id = ?
            ";
            $update_stmt = $this->conn->prepare($update_sql);
            $update_stmt->execute([
                $raw_comment,
                $cleaned_comment,
                $keywords_json,
                $opponent_name,
                $opponent_race,
                $result,
                $map_name,
                $duration,
                $date_played_sql,
                $build_order_json,
                $comment_id
            ]);
        } else {
            // Insert new record
            $insert_sql = "
                INSERT INTO PlayerComments 
                (comment_id, raw_comment, cleaned_comment, keywords, opponent_name, 
                 opponent_race, result, map_name, duration, date_played, build_order, pattern_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ";
            $insert_stmt = $this->conn->prepare($insert_sql);
            $insert_stmt->execute([
                $comment_id,
                $raw_comment,
                $cleaned_comment,
                $keywords_json,
                $opponent_name,
                $opponent_race,
                $result,
                $map_name,
                $duration,
                $date_played_sql,
                $build_order_json
            ]);
        }
        
        return ['success' => true, 'comment_id' => $comment_id];
    }
    
    public function savePatternToDb($pattern_entry) {
        // Save pattern to PatternLearning table
        // pattern_entry should be a JSON string or array containing: signature, comment, game_data, keywords
        
        if (is_string($pattern_entry)) {
            $pattern_entry = json_decode($pattern_entry, true);
        }
        
        $signature = $pattern_entry['signature'] ?? [];
        $comment = $pattern_entry['comment'] ?? '';
        $game_data = $pattern_entry['game_data'] ?? [];
        $keywords = $pattern_entry['keywords'] ?? [];
        
        // Generate pattern_id from signature hash
        $signature_str = json_encode($signature, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $pattern_id = "pattern_" . substr(md5($signature_str), 0, 8);
        
        $signature_json = json_encode($signature, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $metadata_json = json_encode([
            'comment' => $comment,
            'keywords' => $keywords,
            'game_data' => $game_data
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        
        $opponent_race = strtolower($game_data['opponent_race'] ?? '');
        $player_race = strtolower($game_data['player_race'] ?? '');
        $label = !empty($keywords) ? $keywords[0] : '';
        
        // Check if pattern already exists
        $check_sql = "SELECT pattern_id FROM PatternLearning WHERE pattern_id = ?";
        $check_stmt = $this->conn->prepare($check_sql);
        $check_stmt->execute([$pattern_id]);
        $existing = $check_stmt->fetch();
        
        if ($existing) {
            // Update existing pattern (increment game_count)
            $update_sql = "
                UPDATE PatternLearning 
                SET game_count = game_count + 1,
                    updated_at = NOW(),
                    metadata = ?
                WHERE pattern_id = ?
            ";
            $update_stmt = $this->conn->prepare($update_sql);
            $update_stmt->execute([$metadata_json, $pattern_id]);
        } else {
            // Insert new pattern
            $insert_sql = "
                INSERT INTO PatternLearning 
                (pattern_id, signature, label, opponent_race, player_race, game_count, similarity_threshold, metadata)
                VALUES (?, ?, ?, ?, ?, 1, 0.0, ?)
            ";
            $insert_stmt = $this->conn->prepare($insert_sql);
            $insert_stmt->execute([
                $pattern_id,
                $signature_json,
                $label,
                $opponent_race,
                $player_race,
                $metadata_json
            ]);
        }
        
        return ['success' => true, 'pattern_id' => $pattern_id];
    }
    
    public function insertReplayInfo($replay_summary) {
        // Parse replay summary using regex (matching Python implementation)
        if (!preg_match('/Players: ([^:]+): (\w+), ([^:]+): (\w+)/', $replay_summary, $player_matches)) {
            throw new Exception("Unable to find player matches in replay summary");
        }
        
        if (!preg_match('/Winners: (.+?)\n/', $replay_summary, $winners_matches)) {
            throw new Exception("Unable to find winners in replay summary");
        }
        
        if (!preg_match('/Losers: (.+?)\n/', $replay_summary, $losers_matches)) {
            throw new Exception("Unable to find losers in replay summary");
        }
        
        if (!preg_match('/Map: (.+?)\n/', $replay_summary, $map_match)) {
            throw new Exception("Unable to find map in replay summary");
        }
        
        if (!preg_match('/Game Duration: (.+?)\n/', $replay_summary, $game_duration_match)) {
            throw new Exception("Unable to find game duration in replay summary");
        }
        
        if (!preg_match('/Game Type: (.+?)\n/', $replay_summary, $game_type_match)) {
            throw new Exception("Unable to find game type in replay summary");
        }
        
        if (!preg_match('/Region: (.+?)\n/', $replay_summary, $region_match)) {
            throw new Exception("Unable to find region in replay summary");
        }
        
        if (!preg_match('/Timestamp:\s*(\d+)/', $replay_summary, $timestamp_match)) {
            throw new Exception("Unable to find timestamp in replay summary");
        }
        
        $player1_name = trim($player_matches[1]);
        $player1_race = $player_matches[2];
        $player2_name = trim($player_matches[3]);
        $player2_race = $player_matches[4];
        $winner = trim($winners_matches[1]);
        $game_map = trim($map_match[1]);
        $game_duration = trim($game_duration_match[1]);
        $game_type = trim($game_type_match[1]);
        $region = trim($region_match[1]);
        $timestamp = $timestamp_match[1];
        
        // Check if UnixTimestamp already exists
        $sql = "SELECT 1 FROM Replays WHERE UnixTimestamp = ?";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$timestamp]);
        if ($stmt->fetch()) {
            return ['success' => true, 'message' => 'Replay already exists', 'timestamp' => $timestamp];
        }
        
        // Convert Unix timestamp to datetime (US/Eastern timezone)
        $dt = new \DateTime('@' . $timestamp);
        $dt->setTimezone(new \DateTimeZone('America/New_York'));
        $date_played = $dt->format('Y-m-d H:i:s');
        
        // Insert players into Players table
        $sql = "INSERT IGNORE INTO Players (Id, SC2_UserId) VALUES (NULL, ?)";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player1_name]);
        $stmt->execute([$player2_name]);
        
        // Retrieve player IDs
        $sql = "SELECT Id FROM Players WHERE SC2_UserId = ?";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$player1_name]);
        $player1_result = $stmt->fetch();
        $player1_id = $player1_result['Id'] ?? null;
        
        $stmt->execute([$player2_name]);
        $player2_result = $stmt->fetch();
        $player2_id = $player2_result['Id'] ?? null;
        
        // Determine results
        $player1_result = ($winner === $player1_name) ? 'Win' : 'Lose';
        $player2_result = ($winner === $player2_name) ? 'Win' : 'Lose';
        
        // Insert replay details into the Replays table
        $sql = "
            INSERT INTO Replays (
                UnixTimestamp, Player1_Id, Player2_Id, Player1_PickRace, Player2_PickRace,
                Player1_Race, Player2_Race, Player1_Result, Player2_Result,
                Date_Uploaded, Date_Played, Replay_Summary, Map, Region, GameType, GameDuration
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, ?, ?, ?, ?, ?
            )
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([
            $timestamp, $player1_id, $player2_id, $player1_race, $player2_race,
            $player1_race, $player2_race, $player1_result, $player2_result,
            $date_played, $replay_summary, $game_map, $region, $game_type, $game_duration
        ]);
        
        return ['success' => true, 'timestamp' => $timestamp];
    }
}

