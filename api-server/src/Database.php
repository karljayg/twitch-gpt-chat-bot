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
            ORDER BY r.Date_Played DESC
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
                AND r.GameDuration > '00:02:00'
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
    
    public function getReplayById($replay_id) {
        $sql = "SELECT * FROM Replays WHERE Id = ?";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$replay_id]);
        $result = $stmt->fetch();
        return $result ?: null;
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
}

