<?php
namespace PsiStorm\API;

use PDO;
use PDOException;
use Exception;

class Database {
    private $conn;
    private $config;
    private $maxRows;
    private $excludedTables;
    
    public function __construct($config, $maxRows = 1000, $excludedTables = []) {
        $this->config = $config;
        $this->maxRows = $maxRows;
        $this->excludedTables = array_map('strtolower', $excludedTables);
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
    
    /**
     * Check if table is allowed to be queried
     */
    private function isTableAllowed($tableName) {
        return !in_array(strtolower($tableName), $this->excludedTables);
    }
    
    /**
     * Get all tables in the database
     */
    public function getTables() {
        try {
            $stmt = $this->conn->query("SHOW TABLES");
            $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
            
            // Filter out excluded tables
            return array_values(array_filter($tables, function($table) {
                return $this->isTableAllowed($table);
            }));
        } catch (PDOException $e) {
            throw new Exception("Failed to get tables: " . $e->getMessage());
        }
    }
    
    /**
     * Get table schema/structure
     */
    public function getTableSchema($tableName) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        try {
            $stmt = $this->conn->prepare("DESCRIBE `{$tableName}`");
            $stmt->execute();
            return $stmt->fetchAll();
        } catch (PDOException $e) {
            throw new Exception("Failed to get table schema: " . $e->getMessage());
        }
    }
    
    /**
     * Get row count for a table
     */
    public function getTableRowCount($tableName) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        try {
            $stmt = $this->conn->prepare("SELECT COUNT(*) FROM `{$tableName}`");
            $stmt->execute();
            return (int)$stmt->fetchColumn();
        } catch (PDOException $e) {
            throw new Exception("Failed to get row count: " . $e->getMessage());
        }
    }
    
    /**
     * SELECT query with WHERE conditions
     */
    public function select($tableName, $columns = ['*'], $where = [], $orderBy = null, $limit = null, $offset = 0) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        try {
            // Build column list
            $columnList = empty($columns) ? '*' : '`' . implode('`, `', $columns) . '`';
            
            // Build WHERE clause
            $whereClause = '';
            $params = [];
            if (!empty($where)) {
                $conditions = [];
                foreach ($where as $key => $value) {
                    $conditions[] = "`{$key}` = ?";
                    $params[] = $value;
                }
                $whereClause = ' WHERE ' . implode(' AND ', $conditions);
            }
            
            // Build ORDER BY clause
            $orderByClause = '';
            if ($orderBy) {
                $orderByClause = " ORDER BY `{$orderBy['column']}` " . ($orderBy['direction'] ?? 'ASC');
            }
            
            // Build LIMIT clause
            $limit = $limit ? min($limit, $this->maxRows) : $this->maxRows;
            $limitClause = " LIMIT {$limit} OFFSET {$offset}";
            
            $sql = "SELECT {$columnList} FROM `{$tableName}`{$whereClause}{$orderByClause}{$limitClause}";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute($params);
            
            return $stmt->fetchAll();
        } catch (PDOException $e) {
            throw new Exception("SELECT query failed: " . $e->getMessage());
        }
    }
    
    /**
     * INSERT data into table
     */
    public function insert($tableName, $data) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        try {
            $columns = array_keys($data);
            $columnList = '`' . implode('`, `', $columns) . '`';
            $placeholders = implode(', ', array_fill(0, count($columns), '?'));
            
            $sql = "INSERT INTO `{$tableName}` ({$columnList}) VALUES ({$placeholders})";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute(array_values($data));
            
            return [
                'success' => true,
                'insert_id' => $this->conn->lastInsertId(),
                'rows_affected' => $stmt->rowCount()
            ];
        } catch (PDOException $e) {
            throw new Exception("INSERT query failed: " . $e->getMessage());
        }
    }
    
    /**
     * UPDATE data in table
     */
    public function update($tableName, $data, $where) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        if (empty($where)) {
            throw new Exception("UPDATE requires WHERE conditions for safety");
        }
        
        try {
            // Build SET clause
            $setColumns = [];
            $params = [];
            foreach ($data as $key => $value) {
                $setColumns[] = "`{$key}` = ?";
                $params[] = $value;
            }
            $setClause = implode(', ', $setColumns);
            
            // Build WHERE clause
            $whereConditions = [];
            foreach ($where as $key => $value) {
                $whereConditions[] = "`{$key}` = ?";
                $params[] = $value;
            }
            $whereClause = implode(' AND ', $whereConditions);
            
            $sql = "UPDATE `{$tableName}` SET {$setClause} WHERE {$whereClause}";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute($params);
            
            return [
                'success' => true,
                'rows_affected' => $stmt->rowCount()
            ];
        } catch (PDOException $e) {
            throw new Exception("UPDATE query failed: " . $e->getMessage());
        }
    }
    
    /**
     * DELETE from table
     */
    public function delete($tableName, $where) {
        if (!$this->isTableAllowed($tableName)) {
            throw new Exception("Access to table '{$tableName}' is restricted");
        }
        
        if (empty($where)) {
            throw new Exception("DELETE requires WHERE conditions for safety");
        }
        
        try {
            // Build WHERE clause
            $whereConditions = [];
            $params = [];
            foreach ($where as $key => $value) {
                $whereConditions[] = "`{$key}` = ?";
                $params[] = $value;
            }
            $whereClause = implode(' AND ', $whereConditions);
            
            $sql = "DELETE FROM `{$tableName}` WHERE {$whereClause}";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute($params);
            
            return [
                'success' => true,
                'rows_affected' => $stmt->rowCount()
            ];
        } catch (PDOException $e) {
            throw new Exception("DELETE query failed: " . $e->getMessage());
        }
    }
    
    /**
     * Execute custom SQL query (SELECT only for safety)
     */
    public function rawQuery($sql, $params = []) {
        // Only allow SELECT queries in raw mode
        if (!preg_match('/^\s*SELECT\s+/i', trim($sql))) {
            throw new Exception("Only SELECT queries are allowed in raw query mode");
        }
        
        try {
            $stmt = $this->conn->prepare($sql);
            $stmt->execute($params);
            return $stmt->fetchAll();
        } catch (PDOException $e) {
            throw new Exception("Raw query failed: " . $e->getMessage());
        }
    }
}
