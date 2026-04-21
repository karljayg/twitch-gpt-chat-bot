<?php
namespace Mathison\API;

use PDO;
use PDOException;
use Exception;

/**
 * Read-only access to approved psistorm tables for FSL endpoints.
 *
 * Allowed tables (do not query others from this class):
 * Players, Teams, FSL_STATISTICS, fsl_matches, fsl_schedule,
 * fsl_schedule_matches, Player_Aliases (when GRANT allows), users (optional future).
 */
class FslDatabase {
    private $conn;
    private $config;

    public function __construct(array $config) {
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
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4",
            ]);
        } catch (PDOException $e) {
            throw new Exception("FSL database connection failed: " . $e->getMessage());
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
     * Search players by Real_Name substring (case-insensitive).
     */
    public function searchPlayers($query, $limit = 40) {
        if (trim((string) $query) === '') {
            return [];
        }
        $limit = max(1, min(100, (int) $limit));
        $like = '%' . $this->sanitizeLike($query) . '%';
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Team_ID, p.Status, p.User_ID,
                   t.Team_Name
            FROM Players p
            LEFT JOIN Teams t ON t.Team_ID = p.Team_ID
            WHERE LOWER(p.Real_Name) LIKE LOWER(?)
            ORDER BY p.Real_Name ASC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$like]);
        return $stmt->fetchAll();
    }

    /**
     * Single player by Player_ID with team name.
     */
    public function getPlayerById($playerId) {
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Team_ID, p.Status, p.User_ID,
                   p.Championship_Record, p.TeamLeague_Championship_Record, p.Teams_History,
                   p.Intro_Url,
                   t.Team_Name, t.Status AS Team_Status
            FROM Players p
            LEFT JOIN Teams t ON t.Team_ID = p.Team_ID
            WHERE p.Player_ID = ?
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $playerId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /**
     * Resolve first player by exact Real_Name (case-insensitive).
     */
    public function findPlayerByRealNameExact($name) {
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Team_ID, p.Status,
                   t.Team_Name
            FROM Players p
            LEFT JOIN Teams t ON t.Team_ID = p.Team_ID
            WHERE LOWER(p.Real_Name) = LOWER(?)
            ORDER BY p.Player_ID ASC
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([trim($name)]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /**
     * Search teams by Team_Name substring. Empty query lists teams alphabetically (bounded by limit).
     */
    public function searchTeams($query, $limit = 40) {
        $limit = max(1, min(100, (int) $limit));
        if (trim((string) $query) === '') {
            $sql = "
                SELECT Team_ID, Team_Name, Captain_ID, Co_Captain_ID, Status,
                       TeamLeague_Championship_Record
                FROM Teams
                ORDER BY Team_Name ASC
                LIMIT {$limit}
            ";
            $stmt = $this->conn->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll();
        }
        $like = '%' . $this->sanitizeLike($query) . '%';
        $sql = "
            SELECT Team_ID, Team_Name, Captain_ID, Co_Captain_ID, Status,
                   TeamLeague_Championship_Record
            FROM Teams
            WHERE LOWER(Team_Name) LIKE LOWER(?)
            ORDER BY Team_Name ASC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$like]);
        return $stmt->fetchAll();
    }

    public function getTeamById($teamId) {
        $sql = "
            SELECT Team_ID, Team_Name, Captain_ID, Co_Captain_ID, Status,
                   TeamLeague_Championship_Record
            FROM Teams
            WHERE Team_ID = ?
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $teamId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /**
     * Players on a team with display names (Players.Team_ID = team).
     * roster_role: captain | co_captain | member (from Teams.Captain_ID / Co_Captain_ID).
     */
    public function listPlayersForTeam($teamId) {
        $tid = (int) $teamId;
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Status,
                   CASE
                       WHEN p.Player_ID = t.Captain_ID THEN 'captain'
                       WHEN p.Player_ID = t.Co_Captain_ID THEN 'co_captain'
                       ELSE 'member'
                   END AS roster_role
            FROM Players p
            INNER JOIN Teams t ON t.Team_ID = p.Team_ID
            WHERE p.Team_ID = ?
            ORDER BY
                CASE
                    WHEN p.Player_ID = t.Captain_ID THEN 0
                    WHEN p.Player_ID = t.Co_Captain_ID THEN 1
                    ELSE 2
                END,
                p.Real_Name ASC
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$tid]);
        return $stmt->fetchAll();
    }

    /**
     * Team league schedule rows with team names.
     */
    public function listSchedule($season = null, $week = null, $limit = 120) {
        $limit = max(1, min(200, (int) $limit));
        $where = [];
        $params = [];
        if ($season !== null && $season !== '') {
            $where[] = 's.season = ?';
            $params[] = (int) $season;
        }
        if ($week !== null && $week !== '') {
            $where[] = 's.week_number = ?';
            $params[] = (int) $week;
        }
        $sqlWhere = count($where) ? ('WHERE ' . implode(' AND ', $where)) : '';
        $sql = "
            SELECT s.schedule_id, s.season, s.week_number, s.match_date,
                   s.team1_id, s.team2_id, s.team1_score, s.team2_score,
                   s.winner_team_id, s.status, s.notes,
                   t1.Team_Name AS team1_name, t2.Team_Name AS team2_name,
                   tw.Team_Name AS winner_team_name
            FROM fsl_schedule s
            LEFT JOIN Teams t1 ON t1.Team_ID = s.team1_id
            LEFT JOIN Teams t2 ON t2.Team_ID = s.team2_id
            LEFT JOIN Teams tw ON tw.Team_ID = s.winner_team_id
            {$sqlWhere}
            ORDER BY s.match_date DESC, s.schedule_id DESC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    /**
     * Team league season snapshot: standings from schedule rows + winner of highest week_number (often finals proxy).
     */
    public function teamLeagueSeasonSummary($season) {
        $season = (int) $season;
        $sql = "
            SELECT s.schedule_id, s.season, s.week_number, s.match_date,
                   s.team1_id, s.team2_id, s.team1_score, s.team2_score,
                   s.winner_team_id, s.status, s.notes,
                   t1.Team_Name AS team1_name, t2.Team_Name AS team2_name,
                   tw.Team_Name AS winner_team_name
            FROM fsl_schedule s
            LEFT JOIN Teams t1 ON t1.Team_ID = s.team1_id
            LEFT JOIN Teams t2 ON t2.Team_ID = s.team2_id
            LEFT JOIN Teams tw ON tw.Team_ID = s.winner_team_id
            WHERE s.season = ?
            ORDER BY s.week_number ASC, s.schedule_id ASC
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$season]);
        $rows = $stmt->fetchAll();
        $n = count($rows);
        if ($n === 0) {
            return [
                'season' => $season,
                'schedule_rows' => 0,
                'standings' => [],
                'standings_leader_names' => [],
                'standings_tie_at_top' => false,
                'last_week_number' => null,
                'final_week_match' => null,
                'champion_from_final_week_match' => null,
                'note' => 'No fsl_schedule rows for this season.',
            ];
        }

        $stats = [];
        foreach ($rows as $r) {
            $t1 = (int) ($r['team1_id'] ?? 0);
            $t2 = (int) ($r['team2_id'] ?? 0);
            $w = (int) ($r['winner_team_id'] ?? 0);
            if ($t1 <= 0 || $t2 <= 0 || $w <= 0) {
                continue;
            }
            $t1name = $r['team1_name'] ?? '';
            $t2name = $r['team2_name'] ?? '';
            if (!isset($stats[$t1])) {
                $stats[$t1] = ['team_id' => $t1, 'team_name' => $t1name, 'wins' => 0, 'losses' => 0];
            }
            if (!isset($stats[$t2])) {
                $stats[$t2] = ['team_id' => $t2, 'team_name' => $t2name, 'wins' => 0, 'losses' => 0];
            }
            $loser = ($w === $t1) ? $t2 : $t1;
            $stats[$w]['wins']++;
            $stats[$loser]['losses']++;
        }

        $standings = array_values($stats);
        usort($standings, function ($a, $b) {
            if ($a['wins'] !== $b['wins']) {
                return $b['wins'] - $a['wins'];
            }
            return $a['losses'] - $b['losses'];
        });

        $maxW = count($standings) ? (int) $standings[0]['wins'] : 0;
        $leaders = [];
        foreach ($standings as $srow) {
            if ((int) $srow['wins'] === $maxW) {
                $leaders[] = $srow;
            }
        }
        $tieAtTop = count($leaders) > 1;

        $maxWeek = max(array_map(function ($r) {
            return (int) ($r['week_number'] ?? 0);
        }, $rows));
        $finalCandidates = array_values(array_filter($rows, function ($r) use ($maxWeek) {
            return (int) ($r['week_number'] ?? 0) === $maxWeek;
        }));
        usort($finalCandidates, function ($a, $b) {
            $da = $a['match_date'] ?? '';
            $db = $b['match_date'] ?? '';
            $c = strcmp((string) $db, (string) $da);
            if ($c !== 0) {
                return $c;
            }
            return ((int) ($b['schedule_id'] ?? 0)) - ((int) ($a['schedule_id'] ?? 0));
        });
        $finalMatch = count($finalCandidates) ? $finalCandidates[0] : null;
        $championFinal = $finalMatch ? ($finalMatch['winner_team_name'] ?? null) : null;

        return [
            'season' => $season,
            'schedule_rows' => $n,
            'standings' => $standings,
            'standings_leader_names' => array_map(function ($x) {
                return $x['team_name'];
            }, $leaders),
            'standings_tie_at_top' => $tieAtTop,
            'last_week_number' => $maxWeek,
            'final_week_match' => $finalMatch,
            'champion_from_final_week_match' => $championFinal,
            'interpretation_note' => 'champion_from_final_week_match = winner of highest week_number row (often finals); standings_leader_names = most wins in schedule for the season.',
        ];
    }

    /**
     * Solo-league division standings for one season: aggregate series W-L from fsl_matches where
     * t_code is S, A, or B (matches Player_Attributes / spider chart division; see league spec).
     */
    public function soloDivisionSeasonStandings($season, $divisionTCode) {
        $season = (int) $season;
        $dc = strtoupper(trim((string) $divisionTCode));
        if (!in_array($dc, ['S', 'A', 'B'], true)) {
            return [
                'season' => $season,
                'division_t_code' => null,
                'error' => 'division must be S, A, or B (fsl_matches.t_code)',
                'standings' => [],
                'match_row_count' => 0,
                'second_place_player_names' => [],
                'official_champion_from_players_record' => null,
            ];
        }

        // Series W-L plus map differential (sum of map_win−map_loss as winner, inverse as loser)
        // so identical 6–1 records can still order to a single leader when margins differ.
        $sql = "
            SELECT
                agg.player_id,
                pl.Real_Name AS Real_Name,
                agg.wins,
                agg.losses,
                COALESCE(mar.map_margin, 0) AS map_margin
            FROM (
                SELECT
                    x.pid AS player_id,
                    SUM(x.is_win) AS wins,
                    SUM(x.is_loss) AS losses
                FROM (
                    SELECT winner_player_id AS pid, 1 AS is_win, 0 AS is_loss
                    FROM fsl_matches
                    WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, ''))) = ?
                    UNION ALL
                    SELECT loser_player_id, 0, 1
                    FROM fsl_matches
                    WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, ''))) = ?
                ) x
                GROUP BY x.pid
            ) agg
            INNER JOIN Players pl ON pl.Player_ID = agg.player_id
            LEFT JOIN (
                SELECT z.pid, SUM(z.diff) AS map_margin
                FROM (
                    SELECT winner_player_id AS pid, (map_win - map_loss) AS diff
                    FROM fsl_matches
                    WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, ''))) = ?
                    UNION ALL
                    SELECT loser_player_id, (map_loss - map_win) AS diff
                    FROM fsl_matches
                    WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, ''))) = ?
                ) z
                GROUP BY z.pid
            ) mar ON mar.pid = agg.player_id
            ORDER BY agg.wins DESC, agg.losses ASC, COALESCE(mar.map_margin, 0) DESC, pl.Real_Name ASC
        ";

        $bind = [$season, $dc, $season, $dc, $season, $dc, $season, $dc];
        $stmt = $this->conn->prepare($sql);
        $stmt->execute($bind);
        $rows = $stmt->fetchAll();
        $rows = $this->soloDivisionReorderTopTiesByHeadToHead((int) $season, $dc, $rows);

        $cntStmt = $this->conn->prepare(
            'SELECT COUNT(*) FROM fsl_matches WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, \'\'))) = ?'
        );
        $cntStmt->execute([$season, $dc]);
        $matchRowCount = (int) $cntStmt->fetchColumn();

        $standings = [];
        $rank = 1;
        $prevKey = null;
        foreach ($rows as $i => $r) {
            $w = (int) $r['wins'];
            $l = (int) $r['losses'];
            $mm = (int) $r['map_margin'];
            // Rank breaks ties: same series W-L can differ by map_margin (or later by name).
            $key = $w . '-' . $l . '-' . $mm;
            if ($prevKey !== null && $key !== $prevKey) {
                $rank = $i + 1;
            }
            if ($prevKey === null) {
                $rank = 1;
            }
            $prevKey = $key;
            $standings[] = [
                'rank' => $rank,
                'player_id' => (int) $r['player_id'],
                'player_name' => $r['Real_Name'],
                'wins' => $w,
                'losses' => $l,
                'map_margin' => $mm,
            ];
        }

        $secondPlace = [];
        foreach ($standings as $s) {
            if ((int) ($s['rank'] ?? 0) === 2) {
                $secondPlace[] = $s['player_name'];
            }
        }

        $label = $dc === 'S' ? 'Code S' : ($dc === 'A' ? 'Code A' : 'Code B');

        $official = $this->findOfficialSoloDivisionChampionFromPlayersRecord((int) $season, $dc);

        return [
            'season' => $season,
            'division_t_code' => $dc,
            'division_label' => $label,
            'match_row_count' => $matchRowCount,
            'interpretation_note' => 'Who won the division **title** for the season is often stored in Players.Championship_Record (official_champion_from_players_record). Standings below are series W-L from fsl_matches for this season and t_code (schedule performance; ties break by map margin then H2H).',
            'official_champion_from_players_record' => $official,
            'standings' => $standings,
            'second_place_player_names' => $secondPlace,
        ];
    }

    /**
     * Best-effort match on Players.Championship_Record for solo Code S/A/B + season (text or JSON-like).
     * Used when viewers ask "the champion" as the official title, not standings alone.
     *
     * @return array|null { player_id, player_name, championship_record }
     */
    private function findOfficialSoloDivisionChampionFromPlayersRecord($season, $divisionTCode) {
        $season = (int) $season;
        $dc = strtoupper(trim((string) $divisionTCode));
        if (!in_array($dc, ['S', 'A', 'B'], true)) {
            return null;
        }
        $hit = $this->findOfficialSoloDivisionChampionFromChampionshipRecordJson($season, $dc);
        if ($hit !== null) {
            return $hit;
        }
        $hit = $this->findOfficialSoloDivisionChampionFromPlayersRecordStrict($season, $dc);
        if ($hit !== null) {
            return $hit;
        }
        return $this->findOfficialSoloDivisionChampionFromPlayersRecordFallback($season, $dc);
    }

    /**
     * Primary path: structured JSON in Championship_Record — {"records":[{"season":N,"division":"S","result":1},...]}.
     * result === 1 = won the division title that season; result === 2 = lost finals (runner-up) — both mention season+division,
     * so text LIKE alone cannot pick the champion (see e.g. season 3 Code S on psistorm).
     *
     * @return array|null { player_id, player_name, championship_record }
     */
    private function findOfficialSoloDivisionChampionFromChampionshipRecordJson($season, $divisionTCode) {
        $season = (int) $season;
        $dc = strtoupper(trim((string) $divisionTCode));
        if (!in_array($dc, ['S', 'A', 'B'], true)) {
            return null;
        }
        // Narrow candidate set: JSON "season" key with this number (optional space after colon).
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Championship_Record
            FROM Players p
            WHERE p.Championship_Record IS NOT NULL
              AND TRIM(CAST(p.Championship_Record AS CHAR)) <> ''
              AND (
                CAST(p.Championship_Record AS CHAR(16000)) LIKE ?
                OR CAST(p.Championship_Record AS CHAR(16000)) LIKE ?
              )
        ";
        $patTight = '%"season":' . $season . '%';
        $patSpace = '%"season": ' . $season . '%';
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$patTight, $patSpace]);
        $rows = $stmt->fetchAll();
        $winners = [];
        foreach ($rows as $row) {
            $raw = (string) ($row['Championship_Record'] ?? '');
            $data = json_decode($raw, true);
            if (!is_array($data) || !isset($data['records']) || !is_array($data['records'])) {
                continue;
            }
            foreach ($data['records'] as $rec) {
                if (!is_array($rec)) {
                    continue;
                }
                $rSeason = isset($rec['season']) ? (int) $rec['season'] : null;
                if ($rSeason !== $season) {
                    continue;
                }
                $rDiv = isset($rec['division']) ? strtoupper(trim((string) $rec['division'])) : '';
                if ($rDiv !== $dc) {
                    continue;
                }
                $rResult = isset($rec['result']) ? (int) $rec['result'] : null;
                if ($rResult !== 1) {
                    continue;
                }
                $winners[] = [
                    'player_id' => (int) $row['Player_ID'],
                    'player_name' => $row['Real_Name'],
                    'championship_record' => $row['Championship_Record'],
                ];
                break;
            }
        }
        if (!count($winners)) {
            return $this->soloDivisionChampionFromFinalsNotes($season, $dc, $rows);
        }
        if (count($winners) > 1) {
            usort($winners, function ($a, $b) {
                return ((int) $a['player_id']) <=> ((int) $b['player_id']);
            });
        }
        return $winners[0];
    }

    /**
     * When result===1 was never written on the winner row, runner-up rows often still carry
     * notes like "S : Winner def. Loser 4-3" with result===2 — infer the champion name.
     *
     * @param array $rows Same candidate rows as JSON primary path (Players with this season in JSON).
     * @return array|null { player_id, player_name, championship_record }
     */
    private function soloDivisionChampionFromFinalsNotes($season, $dc, array $rows) {
        $season = (int) $season;
        $dc = strtoupper(trim((string) $dc));
        $names = [];
        foreach ($rows as $row) {
            $raw = (string) ($row['Championship_Record'] ?? '');
            $data = json_decode($raw, true);
            if (!is_array($data) || !isset($data['records']) || !is_array($data['records'])) {
                continue;
            }
            foreach ($data['records'] as $rec) {
                if (!is_array($rec)) {
                    continue;
                }
                $rSeason = isset($rec['season']) ? (int) $rec['season'] : null;
                if ($rSeason !== $season) {
                    continue;
                }
                $rDiv = isset($rec['division']) ? strtoupper(trim((string) $rec['division'])) : '';
                if ($rDiv !== $dc) {
                    continue;
                }
                $notes = isset($rec['notes']) ? trim((string) $rec['notes']) : '';
                if ($notes === '') {
                    continue;
                }
                // Typical finals line: "S : NameA def. NameB 4-3" or "Code S : ..."
                if (preg_match('/:\s*(.+?)\s+def\.?\s+(.+?)\s+\d/u', $notes, $m)) {
                    $winnerName = trim($m[1]);
                    if ($winnerName !== '') {
                        $names[$winnerName] = true;
                    }
                }
            }
        }
        $uniq = array_keys($names);
        if (count($uniq) !== 1) {
            return null;
        }
        $pl = $this->findPlayerByRealNameExact($uniq[0]);
        if ($pl === null) {
            return null;
        }
        $pid = (int) $pl['Player_ID'];
        $full = $this->getPlayerById($pid);
        if ($full === null) {
            return null;
        }
        return [
            'player_id' => $pid,
            'player_name' => $full['Real_Name'],
            'championship_record' => $full['Championship_Record'],
        ];
    }

    /**
     * Strict SQL LIKE on Championship_Record (season + division substrings).
     */
    private function findOfficialSoloDivisionChampionFromPlayersRecordStrict($season, $dc) {
        $divLikes = [
            'S' => ['%code s%', '%code-s%', '%"s"%', '%t_code":"s"%', '%division":"s"%'],
            'A' => ['%code a%', '%code-a%', '%"a"%', '%t_code":"a"%', '%division":"a"%'],
            'B' => ['%code b%', '%code-b%', '%"b"%', '%t_code":"b"%', '%division":"b"%'],
        ];
        $seasonLikes = [
            '%season ' . $season . '%',
            '%season' . $season . '%',
            '% s' . $season . '%',
            '%(s' . $season . ')%',
            '%"' . $season . '"%',
            '%:' . $season . ',%',
            '%:' . $season . ']%',
            '%:' . $season . '}%',
            '%season":' . $season . '%',
            '%Season ' . $season . '%',
        ];
        $whereDiv = '(' . implode(' OR ', array_fill(0, count($divLikes[$dc]), 'LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE ?')) . ')';
        $whereSeason = '(' . implode(' OR ', array_fill(0, count($seasonLikes), 'LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE ?')) . ')';
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Championship_Record
            FROM Players p
            WHERE p.Championship_Record IS NOT NULL
              AND TRIM(CAST(p.Championship_Record AS CHAR)) <> ''
              AND {$whereSeason}
              AND {$whereDiv}
            ORDER BY
              CASE WHEN LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%champion%' THEN 0 ELSE 1 END,
              CASE WHEN LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%winner%' THEN 0 ELSE 1 END,
              p.Player_ID ASC
            LIMIT 5
        ";
        $params = array_merge(
            array_map('strtolower', $seasonLikes),
            array_map('strtolower', $divLikes[$dc])
        );
        $stmt = $this->conn->prepare($sql);
        $stmt->execute($params);
        $rows = $stmt->fetchAll();
        if (!count($rows)) {
            return null;
        }
        $top = $rows[0];
        return [
            'player_id' => (int) $top['Player_ID'],
            'player_name' => $top['Real_Name'],
            'championship_record' => $top['Championship_Record'],
        ];
    }

    /**
     * Broader candidate pull + PHP checks when stored text does not match strict LIKE patterns.
     */
    private function findOfficialSoloDivisionChampionFromPlayersRecordFallback($season, $dc) {
        $divLikes = [
            'S' => ['%code s%', '%code-s%', '%"s"%'],
            'A' => ['%code a%', '%code-a%', '%"a"%'],
            'B' => ['%code b%', '%code-b%', '%"b"%'],
        ];
        $whereDiv = '(' . implode(' OR ', array_fill(0, count($divLikes[$dc]), 'LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE ?')) . ')';
        $sql = "
            SELECT p.Player_ID, p.Real_Name, p.Championship_Record
            FROM Players p
            WHERE p.Championship_Record IS NOT NULL
              AND TRIM(CAST(p.Championship_Record AS CHAR)) <> ''
              AND {$whereDiv}
              AND (
                LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%champion%'
                OR LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%winner%'
                OR LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%1st%'
                OR LOWER(CAST(p.Championship_Record AS CHAR(8000))) LIKE '%first place%'
              )
            ORDER BY p.Player_ID ASC
            LIMIT 80
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute(array_map('strtolower', $divLikes[$dc]));
        $rows = $stmt->fetchAll();
        $best = null;
        $bestScore = -1;
        foreach ($rows as $row) {
            $cr = strtolower((string) ($row['Championship_Record'] ?? ''));
            if (!$this->championshipRecordReferencesSeason($cr, (int) $season)) {
                continue;
            }
            $score = 0;
            if (strpos($cr, 'champion') !== false) {
                $score += 10;
            }
            if (strpos($cr, 'winner') !== false) {
                $score += 5;
            }
            if (strpos($cr, '1st') !== false || strpos($cr, 'first') !== false) {
                $score += 3;
            }
            if ($score > $bestScore) {
                $bestScore = $score;
                $best = $row;
            }
        }
        if ($best === null) {
            return null;
        }
        return [
            'player_id' => (int) $best['Player_ID'],
            'player_name' => $best['Real_Name'],
            'championship_record' => $best['Championship_Record'],
        ];
    }

    /**
     * Loose season reference check on lowercased Championship_Record text.
     */
    private function championshipRecordReferencesSeason($lowerCr, $season) {
        $s = (int) $season;
        if (preg_match('/season\s*' . $s . '([^0-9]|$)/', $lowerCr)) {
            return true;
        }
        if (strpos($lowerCr, '"season":' . $s) !== false || strpos($lowerCr, '"season": ' . $s) !== false) {
            return true;
        }
        if (strpos($lowerCr, 'season ' . $s) !== false) {
            return true;
        }
        if (preg_match('/\bs' . $s . '\b/', $lowerCr)) {
            return true;
        }
        if (strpos($lowerCr, '(' . $s . ')') !== false) {
            return true;
        }
        return false;
    }

    /**
     * When multiple players share best wins/losses/map_margin at the top, order by wins in
     * head-to-head matches between those players only (same season + t_code).
     */
    private function soloDivisionReorderTopTiesByHeadToHead($season, $divisionTCode, array $rows): array {
        if (count($rows) < 2) {
            return $rows;
        }
        $w0 = (int) $rows[0]['wins'];
        $l0 = (int) $rows[0]['losses'];
        $m0 = (int) $rows[0]['map_margin'];
        $k = 0;
        $n = count($rows);
        for (; $k < $n; $k++) {
            $r = $rows[$k];
            if ((int) $r['wins'] !== $w0 || (int) $r['losses'] !== $l0 || (int) $r['map_margin'] !== $m0) {
                break;
            }
        }
        if ($k < 2) {
            return $rows;
        }
        $ids = [];
        for ($i = 0; $i < $k; $i++) {
            $ids[] = (int) $rows[$i]['player_id'];
        }
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $sql = "
            SELECT winner_player_id AS pid, COUNT(*) AS h2h_wins
            FROM fsl_matches
            WHERE season = ? AND UPPER(TRIM(COALESCE(t_code, ''))) = ?
              AND winner_player_id IN ($placeholders)
              AND loser_player_id IN ($placeholders)
            GROUP BY winner_player_id
        ";
        $params = array_merge([(int) $season, (string) $divisionTCode], $ids, $ids);
        $stmt = $this->conn->prepare($sql);
        $stmt->execute($params);
        $winCounts = [];
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $winCounts[(int) $row['pid']] = (int) $row['h2h_wins'];
        }
        $indices = range(0, $k - 1);
        usort($indices, function ($a, $b) use ($rows, $winCounts) {
            $ida = (int) $rows[$a]['player_id'];
            $idb = (int) $rows[$b]['player_id'];
            $wa = $winCounts[$ida] ?? 0;
            $wb = $winCounts[$idb] ?? 0;
            if ($wa !== $wb) {
                return $wb <=> $wa;
            }
            return strcasecmp((string) $rows[$a]['Real_Name'], (string) $rows[$b]['Real_Name']);
        });
        $newTop = [];
        foreach ($indices as $i) {
            $newTop[] = $rows[$i];
        }
        return array_merge($newTop, array_slice($rows, $k));
    }

    /**
     * fsl_matches with winner/loser display names.
     * Optional filters: season, player_id OR (player_name), OR (player_name + opponent_name) for head-to-head only.
     */
    public function listMatches($season = null, $playerNameQuery = null, $playerId = null, $limit = 60, $opponentNameQuery = null) {
        $limit = max(1, min(150, (int) $limit));
        $where = [];
        $params = [];

        if ($season !== null && $season !== '') {
            $where[] = 'm.season = ?';
            $params[] = (int) $season;
        }

        if ($playerId !== null && $playerId !== '') {
            $where[] = '(m.winner_player_id = ? OR m.loser_player_id = ?)';
            $pid = (int) $playerId;
            $params[] = $pid;
            $params[] = $pid;
        } elseif (
            $playerNameQuery !== null && trim($playerNameQuery) !== ''
            && $opponentNameQuery !== null && trim($opponentNameQuery) !== ''
        ) {
            $like1 = '%' . $this->sanitizeLike($playerNameQuery) . '%';
            $like2 = '%' . $this->sanitizeLike($opponentNameQuery) . '%';
            $where[] = '(
                (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?))
                OR (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?))
            )';
            $params[] = $like1;
            $params[] = $like2;
            $params[] = $like2;
            $params[] = $like1;
        } elseif ($playerNameQuery !== null && trim($playerNameQuery) !== '') {
            $like = '%' . $this->sanitizeLike($playerNameQuery) . '%';
            $where[] = '(LOWER(w.Real_Name) LIKE LOWER(?) OR LOWER(l.Real_Name) LIKE LOWER(?))';
            $params[] = $like;
            $params[] = $like;
        }

        $sqlWhere = count($where) ? ('WHERE ' . implode(' AND ', $where)) : '';

        $sql = "
            SELECT m.fsl_match_id, m.season, m.season_extra_info, m.notes, m.t_code,
                   m.winner_player_id, m.winner_race, m.map_win, m.map_loss,
                   m.loser_player_id, m.loser_race, m.best_of,
                   m.winner_team_id, m.loser_team_id, m.source, m.vod,
                   w.Real_Name AS winner_name, l.Real_Name AS loser_name
            FROM fsl_matches m
            JOIN Players w ON w.Player_ID = m.winner_player_id
            JOIN Players l ON l.Player_ID = m.loser_player_id
            {$sqlWhere}
            ORDER BY m.fsl_match_id DESC
            LIMIT {$limit}
        ";

        $stmt = $this->conn->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    /**
     * Career head-to-head aggregates between two players (same name LIKE rules as listMatches H2H).
     * Map columns: map_win = maps winner took; map_loss = maps loser took in that series.
     */
    public function aggregateHeadToHead($playerNameQuery, $opponentNameQuery, $season = null) {
        $playerNameQuery = trim((string) $playerNameQuery);
        $opponentNameQuery = trim((string) $opponentNameQuery);
        if ($playerNameQuery === '' || $opponentNameQuery === '') {
            return null;
        }
        $like1 = '%' . $this->sanitizeLike($playerNameQuery) . '%';
        $like2 = '%' . $this->sanitizeLike($opponentNameQuery) . '%';

        $h2hWhere = '(
                (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?))
                OR (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?))
            )';
        $where = [$h2hWhere];
        $params = [$like1, $like2, $like2, $like1];

        if ($season !== null && $season !== '') {
            $where[] = 'm.season = ?';
            $params[] = (int) $season;
        }
        $sqlWhere = 'WHERE ' . implode(' AND ', $where);

        // Bind order: WHERE (4 or 5 with season), then each SUM branch uses like1/like2 patterns.
        $sql = "
            SELECT
                COUNT(*) AS series_total,
                COALESCE(SUM(CASE
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN 1
                    ELSE 0 END), 0) AS series_wins_a,
                COALESCE(SUM(CASE
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN 1
                    ELSE 0 END), 0) AS series_wins_b,
                COALESCE(SUM(CASE
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN m.map_win
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN m.map_loss
                    ELSE 0 END), 0) AS maps_won_a,
                COALESCE(SUM(CASE
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN m.map_loss
                    WHEN (LOWER(w.Real_Name) LIKE LOWER(?) AND LOWER(l.Real_Name) LIKE LOWER(?)) THEN m.map_win
                    ELSE 0 END), 0) AS maps_won_b,
                MIN(m.fsl_match_id) AS first_match_id,
                MAX(m.fsl_match_id) AS last_match_id
            FROM fsl_matches m
            JOIN Players w ON w.Player_ID = m.winner_player_id
            JOIN Players l ON l.Player_ID = m.loser_player_id
            {$sqlWhere}
        ";

        $selectParams = [
            $like1, $like2,
            $like2, $like1,
            $like1, $like2, $like2, $like1,
            $like1, $like2, $like2, $like1,
        ];
        $stmt = $this->conn->prepare($sql);
        $stmt->execute(array_merge($params, $selectParams));
        $row = $stmt->fetch();
        if ($row === false) {
            return null;
        }

        $seriesTotal = (int) $row['series_total'];
        $wa = (int) $row['series_wins_a'];
        $wb = (int) $row['series_wins_b'];
        $mapsA = (int) $row['maps_won_a'];
        $mapsB = (int) $row['maps_won_b'];

        // Laplace (add-one) next-series win probability from series record only (naive).
        $nextA = null;
        $nextB = null;
        if ($seriesTotal > 0) {
            $nextA = ($wa + 1) / ($seriesTotal + 2);
            $nextB = ($wb + 1) / ($seriesTotal + 2);
        }

        return [
            'player_a_query' => $playerNameQuery,
            'player_b_query' => $opponentNameQuery,
            'season_filter' => $season !== null && $season !== '' ? (int) $season : null,
            'series_total' => $seriesTotal,
            'series_wins_a' => $wa,
            'series_wins_b' => $wb,
            'maps_won_a' => $mapsA,
            'maps_won_b' => $mapsB,
            'first_match_id' => isset($row['first_match_id']) ? (int) $row['first_match_id'] : null,
            'last_match_id' => isset($row['last_match_id']) ? (int) $row['last_match_id'] : null,
            'next_series_win_prob_a' => $nextA,
            'next_series_win_prob_b' => $nextB,
            'empirical_model' => 'laplace_series_record',
            'empirical_note' => 'Win probabilities use add-one smoothing on historical series wins only (not map scores, not other players).',
        ];
    }

    public function getMatchById($fslMatchId) {
        $sql = "
            SELECT m.fsl_match_id, m.season, m.season_extra_info, m.notes, m.t_code,
                   m.winner_player_id, m.winner_race, m.map_win, m.map_loss,
                   m.loser_player_id, m.loser_race, m.best_of,
                   m.winner_team_id, m.loser_team_id, m.source, m.vod,
                   w.Real_Name AS winner_name, l.Real_Name AS loser_name
            FROM fsl_matches m
            JOIN Players w ON w.Player_ID = m.winner_player_id
            JOIN Players l ON l.Player_ID = m.loser_player_id
            WHERE m.fsl_match_id = ?
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $fslMatchId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /**
     * FSL_STATISTICS rows for a player (per division/race/alias).
     */
    public function listStatisticsForPlayer($playerId) {
        $sql = "
            SELECT s.Player_Record_ID, s.Player_ID, s.Alias_ID, s.Division, s.Race,
                   s.MapsW, s.MapsL, s.SetsW, s.SetsL
            FROM FSL_STATISTICS s
            WHERE s.Player_ID = ?
            ORDER BY s.Division ASC, s.Race ASC
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $playerId]);
        return $stmt->fetchAll();
    }

    /**
     * Career match win percentage from fsl_matches (each row = one series).
     * Requires minimum completed series (wins + losses) to qualify.
     */
    public function leaderboardMatchWinPct($minMatches = 10, $limit = 15) {
        $minMatches = max(1, min(500, (int) $minMatches));
        $limit = max(1, min(50, (int) $limit));
        $sql = "
            SELECT
                p.Player_ID,
                p.Real_Name,
                agg.wins,
                agg.losses,
                (agg.wins + agg.losses) AS matches_played,
                (agg.wins / (agg.wins + agg.losses)) AS win_pct
            FROM (
                SELECT
                    pid,
                    SUM(is_win) AS wins,
                    SUM(is_loss) AS losses
                FROM (
                    SELECT winner_player_id AS pid, 1 AS is_win, 0 AS is_loss FROM fsl_matches
                    UNION ALL
                    SELECT loser_player_id, 0, 1 FROM fsl_matches
                ) x
                GROUP BY pid
                HAVING (SUM(is_win) + SUM(is_loss)) >= ?
            ) agg
            INNER JOIN Players p ON p.Player_ID = agg.pid
            ORDER BY win_pct DESC, matches_played DESC, p.Real_Name ASC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$minMatches]);
        return $stmt->fetchAll();
    }

    /**
     * Career series **wins** (count as winner in fsl_matches), ordered by wins descending.
     */
    public function leaderboardMatchTotalWins($minMatches = 1, $limit = 15) {
        $minMatches = max(1, min(500, (int) $minMatches));
        $limit = max(1, min(50, (int) $limit));
        $sql = "
            SELECT
                p.Player_ID,
                p.Real_Name,
                agg.wins,
                agg.losses,
                (agg.wins + agg.losses) AS matches_played,
                (agg.wins / (agg.wins + agg.losses)) AS win_pct
            FROM (
                SELECT
                    pid,
                    SUM(is_win) AS wins,
                    SUM(is_loss) AS losses
                FROM (
                    SELECT winner_player_id AS pid, 1 AS is_win, 0 AS is_loss FROM fsl_matches
                    UNION ALL
                    SELECT loser_player_id, 0, 1 FROM fsl_matches
                ) x
                GROUP BY pid
                HAVING (SUM(is_win) + SUM(is_loss)) >= ?
            ) agg
            INNER JOIN Players p ON p.Player_ID = agg.pid
            ORDER BY agg.wins DESC, (agg.wins + agg.losses) DESC, p.Real_Name ASC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([$minMatches]);
        return $stmt->fetchAll();
    }

    /**
     * Career map wins from FSL_STATISTICS: one row per (Player_ID, Division, Race) via MIN(Alias_ID),
     * then SUM — matches player_statistics.php / avoids double-count when multiple aliases duplicate splits.
     */
    public function leaderboardStatisticsMapsWon($limit = 15) {
        $limit = max(1, min(50, (int) $limit));
        $sql = "
            SELECT
                p.Player_ID,
                p.Real_Name,
                SUM(s.MapsW) AS total_maps_w,
                SUM(s.MapsL) AS total_maps_l
            FROM FSL_STATISTICS s
            INNER JOIN Players p ON p.Player_ID = s.Player_ID
            INNER JOIN (
                SELECT Player_ID, Division, Race, MIN(Alias_ID) AS Alias_ID
                FROM FSL_STATISTICS
                GROUP BY Player_ID, Division, Race
            ) pick
                ON s.Player_ID = pick.Player_ID
                AND s.Division <=> pick.Division
                AND s.Race <=> pick.Race
                AND s.Alias_ID = pick.Alias_ID
            GROUP BY p.Player_ID, p.Real_Name
            HAVING SUM(s.MapsW) > 0
            ORDER BY total_maps_w DESC, total_maps_l ASC, p.Real_Name ASC
            LIMIT {$limit}
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /**
     * Schedule ↔ match linkage for a schedule row (optional drill-down).
     */
    public function listScheduleMatchesForSchedule($scheduleId) {
        $sql = "
            SELECT sm.id, sm.schedule_id, sm.fsl_match_id, sm.match_type, sm.created_at
            FROM fsl_schedule_matches sm
            WHERE sm.schedule_id = ?
            ORDER BY sm.id ASC
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $scheduleId]);
        return $stmt->fetchAll();
    }

    /**
     * Single schedule row by id with team names.
     */
    public function getScheduleById($scheduleId) {
        $sql = "
            SELECT s.schedule_id, s.season, s.week_number, s.match_date,
                   s.team1_id, s.team2_id, s.team1_score, s.team2_score,
                   s.winner_team_id, s.status, s.notes,
                   t1.Team_Name AS team1_name, t2.Team_Name AS team2_name,
                   tw.Team_Name AS winner_team_name
            FROM fsl_schedule s
            LEFT JOIN Teams t1 ON t1.Team_ID = s.team1_id
            LEFT JOIN Teams t2 ON t2.Team_ID = s.team2_id
            LEFT JOIN Teams tw ON tw.Team_ID = s.winner_team_id
            WHERE s.schedule_id = ?
            LIMIT 1
        ";
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([(int) $scheduleId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    private function sanitizeLike($raw) {
        return str_replace(['%', '_'], ['\\%', '\\_'], $raw);
    }
}
