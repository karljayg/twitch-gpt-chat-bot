import mysql.connector.pooling
from mysql.connector import Error
import time
import sys
import re
import logging
import pytz
import traceback
from datetime import datetime, timedelta
from settings import config


class Database:
    def __init__(self):
        # Connection pool initialization
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=5,
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )

        # Logging setup
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("db_logger")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        log_file_name = f"logs/db_{timestamp}.log"
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Connection setup
        self.connection = self.pool.get_connection()
        self.cursor = self.connection.cursor(dictionary=True, buffered=True)

    def ensure_connection(self):
        """
        Ensures that the database connection is alive, reconnecting if necessary.
        """
        try:
            if not self.connection.is_connected():
                self.logger.debug("Re-establishing a lost database connection.")
                self.connection = self.pool.get_connection()
        except Error as e:
            self.logger.error(f"Error while re-establishing connection: {e}")
            self.connection = self.pool.get_connection()
        return self.connection        

    # override execute with retry logic due to DB connection issues
    def execute(self, sql, data=None):
        try:
            _retries = 3
            _delay = 2
            conn = self.ensure_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, data)
            result = cursor.fetchall()
            conn.commit()
            return result if cursor.description else cursor.lastrowid
        except Error as e:
            if _retries > 0:
                self.logger.debug(f"encountered error: {e}, wait and retry #{_retries}")
                time.sleep(_delay)
                return self.execute(sql, data)
            else:
                raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def create_user(self, data):
        sql = "INSERT INTO USER (LastName, DisplayName, TwitchName, Gender, Sex, Dob, Race, Nationality, Occupation, State, Country) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        self.cursor.execute(sql, data)
        self.connection.commit()

    def read_user(self, user_id):
        sql = "SELECT * FROM USER WHERE id=%s"
        self.cursor.execute(sql, (user_id,))
        return self.cursor.fetchone()

    def update_user(self, user_id, data):
        sql = "UPDATE USER SET LastName=%s, DisplayName=%s, TwitchName=%s, Gender=%s, Sex=%s, Dob=%s, Race=%s, Nationality=%s, Occupation=%s, State=%s, Country=%s WHERE id=%s"
        self.cursor.execute(sql, (*data, user_id))
        self.connection.commit()

    def delete_user(self, user_id):
        sql = "DELETE FROM USER WHERE id=%s"
        self.cursor.execute(sql, (user_id,))
        self.connection.commit()

    # --- MAJOR_TRAITS ---
    def create_major_trait(self, data):
        sql = "INSERT INTO MAJOR_TRAITS (Name, Description) VALUES (%s, %s)"
        self.cursor.execute(sql, data)
        self.connection.commit()
        return self.cursor.lastrowid

    def read_major_trait(self, id):
        sql = "SELECT * FROM MAJOR_TRAITS WHERE id=%s"
        self.cursor.execute(sql, (id,))
        return self.cursor.fetchone()

    def update_major_trait(self, id, data):
        sql = "UPDATE MAJOR_TRAITS SET Name=%s, Description=%s WHERE id=%s"
        self.cursor.execute(sql, (*data, id))
        self.connection.commit()

    def delete_major_trait(self, id):
        sql = "DELETE FROM MAJOR_TRAITS WHERE id=%s"
        self.cursor.execute(sql, (id,))
        self.connection.commit()

    def connect(self):
        # Connect to the database and create a cursor
        self.connection = ...  # your connection logic
        self.cursor = self.connection.cursor()

    def close(self):
        # Close the cursor and connection
        self.cursor.close()
        self.connection.close()

    def check_player_exists(self, player_name, player_race):
        self.cursor.reset()
        try:
            # Define the query with JOIN to include player names
            query = """
                SELECT 
                    r.*, 
                    p1.SC2_UserId AS Player1_Name, 
                    p2.SC2_UserId AS Player2_Name
                FROM 
                    Replays r
                    JOIN Players p1 ON r.Player1_Id = p1.Id
                    JOIN Players p2 ON r.Player2_Id = p2.Id
                WHERE 
                    (p1.SC2_UserId = %s AND r.Player1_Race = %s) 
                    OR 
                    (p2.SC2_UserId = %s AND r.Player2_Race = %s)
                ORDER BY 
                    r.Date_Played DESC
                LIMIT 1;
            """

            # Execute the query
            self.cursor.execute(query, (player_name, player_race, player_name, player_race))

            # Fetch the result
            result = self.cursor.fetchone()

            # Return the replay summary if found, else None
            if result:
                self.logger.debug(f"Player exists: {result}")
                return result
            else:
                self.logger.debug("Player does not exist in our DB")
                return None
        except Exception as e:
            self.logger.error(f"Error checking if player exists: {e}")
            return None

    def get_player_records(self, player_name):
        # Reset the cursor if needed
        self.cursor.reset()

        # SQL Query
        sql = """
        SELECT 
            CASE 
                WHEN p1.SC2_UserId = %s THEN p2.SC2_UserId
                ELSE p1.SC2_UserId 
            END AS Opponent,
            SUM(CASE WHEN (p1.SC2_UserId = %s AND r.Player1_Result = 'Win') OR (p2.SC2_UserId = %s AND r.Player2_Result = 'Win') THEN 1 ELSE 0 END) AS Wins,
            SUM(CASE WHEN (p1.SC2_UserId = %s AND r.Player1_Result = 'Lose') OR (p2.SC2_UserId = %s AND r.Player2_Result = 'Lose') THEN 1 ELSE 0 END) AS Losses,
            MAX(r.Date_Played) AS Last_Played
        FROM 
            Replays r
        JOIN 
            Players p1 ON r.Player1_Id = p1.Id
        JOIN 
            Players p2 ON r.Player2_Id = p2.Id
        WHERE 
            p1.SC2_UserId = %s OR p2.SC2_UserId = %s
        GROUP BY 
            Opponent
        ORDER BY 
            Last_Played DESC;
        """

        # Execute the query
        self.cursor.execute(sql, (player_name, player_name, player_name, player_name, player_name, player_name, player_name))
        results = self.cursor.fetchall()

        # Formatting results
        formatted_results = []
        for row in results:
            opponent, wins, losses = row['Opponent'], row['Wins'], row['Losses']
            formatted_result = f"{player_name}, {opponent}, {wins} wins, {losses} losses"
            formatted_results.append(formatted_result)

        self.logger.debug(f"result: \n {formatted_results}")

        return formatted_results

    def get_games_for_last_x_hours(self, hours):
        # Calculate the start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        formatted_start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
        formatted_end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")

        # SQL Query
        sql = """
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
            r.Date_Played >= %s AND r.Date_Played <= %s
        ORDER BY 
            r.Date_Played DESC;
        """

        # Execute the query
        self.cursor.execute(sql, (formatted_start_date, formatted_end_date))
        results = self.cursor.fetchall()

        # Formatting results
        formatted_results = []
        for row in results:
            game_info = f"{row['Players']} on {row['Map']}, Winner: {row['Winner']}, Played at: {row['Date_Played'].strftime('%Y-%m-%d %H:%M:%S')}"
            formatted_results.append(game_info)

        return formatted_results

    def convertUnixToDatetime(self, timestamp, timezone='US/Eastern'):
        # Convert the Unix timestamp to US Eastern time
        utc_dt = datetime.utcfromtimestamp(int(timestamp))
        if timezone == "US/Eastern":
            eastern = pytz.timezone('US/Eastern')
            utc_dt = pytz.utc.localize(utc_dt)
            eastern_dt = utc_dt.astimezone(eastern)
            date_played = eastern_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.logger.error(
                "Timezone not supported at the moment. Please use US/Eastern.")
            return None
        return date_played

    def insert_replay_info(self, replay_summary):
        # The replay summary
        # with open("temp/replay_summary.txt", "r") as file:
        #    replay_summary = file.read()

        try:

            # Extract details using regex
            # player_matches = re.search(r"Players: (\w+): (\w+), (\w+): (\w+)", replay_summary)
            player_matches = re.search(
                r"Players: (\w+[^:]+): (\w+), (\w+[^:]+): (\w+)", replay_summary)

            winners_matches = re.search(r"Winners: (.+?)\n", replay_summary)
            losers_matches = re.search(r"Losers: (.+?)\n", replay_summary)
            map_match = re.search(r"Map: (.+?)\n", replay_summary)
            game_duration_match = re.search(
                r"Game Duration: (.+?)\n", replay_summary)
            game_type_match = re.search(r"Game Type: (.+?)\n", replay_summary)
            region_match = re.search(r"Region: (.+?)\n", replay_summary)
            timestamp_match = re.search(r'Timestamp:\s*(\d+)', replay_summary)

            # Extracted details
            if not player_matches:
                self.logger.debug(
                    f"Unable to find player matches in replay summary: {replay_summary}")
                return
            player1_name, player1_race, player2_name, player2_race = player_matches.groups()

            winner = winners_matches.group(1)
            loser = losers_matches.group(1)
            game_map = map_match.group(1)
            game_duration = game_duration_match.group(1)
            game_type = game_type_match.group(1)
            region = region_match.group(1)
            timestamp = timestamp_match.group(1)

            # Check if UnixTimestamp already exists
            self.cursor.execute(
                "SELECT 1 FROM Replays WHERE UnixTimestamp = %s", (timestamp,))
            existing_entry = self.cursor.fetchall()

            date_played = self.convertUnixToDatetime(timestamp, "US/Eastern")

            if existing_entry:
                self.logger.debug(
                    f"Entry with UnixTimestamp {timestamp} already exists in the database.")
                return

            # Insert players into the Players table
            for player, race in [(player1_name, player1_race), (player2_name, player2_race)]:
                self.cursor.execute(
                    "INSERT IGNORE INTO Players (Id, SC2_UserId) VALUES (NULL, %s)", (player,))

            # Retrieve player IDs
            self.cursor.execute(
                "SELECT Id FROM Players WHERE SC2_UserId = %s", (player1_name,))
            player1_result = self.cursor.fetchone()
            if player1_result:
                # Assuming you know the key:
                # player1_id = player1_result['Id']

                # If you want the first value without knowing the key:
                player1_id = next(iter(player1_result.values()))
            else:
                player1_id = None

            self.cursor.execute(
                "SELECT Id FROM Players WHERE SC2_UserId = %s", (player2_name,))
            player2_result = self.cursor.fetchone()
            if player2_result:
                # Assuming you know the key:
                # player2_id = player2_result['Id']

                # If you want the first value without knowing the key:
                player2_id = next(iter(player2_result.values()))
            else:
                player2_id = None

            # Insert replay details into the Replays table
            self.cursor.execute("""
                INSERT INTO Replays (
                    UnixTimestamp, Player1_Id, Player2_Id, Player1_PickRace, Player2_PickRace,
                    Player1_Race, Player2_Race, Player1_Result, Player2_Result,
                    Date_Uploaded, Date_Played, Replay_Summary, Map, Region, GameType, GameDuration
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s
                )
            """, (timestamp, player1_id, player2_id, player1_race, player2_race, player1_race, player2_race,
                  'Win' if winner == player1_name else 'Lose',
                  'Win' if winner == player2_name else 'Lose',
                  date_played, replay_summary, game_map, region, game_type, game_duration))
            self.connection.commit()
            self.logger.debug(
                f"Inserted replay info with UnixTimestamp {timestamp}")
            return True

        except Exception as e:
            error_message = str(e) + "\n" + traceback.format_exc()
            self.logger.error(f"Error inserting replay info: {error_message}")

    def extract_opponent_build_order(self, opponent_name, opp_race, streamer_picked_race):
        self.logger.debug(f"searching in DB for {opponent_name} with race {opp_race} against {streamer_picked_race}")
        # SQL to get the latest game of the opponent from the Replays table with race conditions
        sql = """
        SELECT r.Replay_Summary
        FROM Replays r
        JOIN Players p1 ON r.Player1_Id = p1.Id
        JOIN Players p2 ON r.Player2_Id = p2.Id
        WHERE ((p1.SC2_UserId = %s AND r.Player2_PickRace = %s) OR (p2.SC2_UserId = %s AND r.Player1_PickRace = %s)) 
        AND ((p1.SC2_UserId = %s AND r.Player1_Race = %s) OR (p2.SC2_UserId = %s AND r.Player2_Race = %s))
        ORDER BY r.Date_Played DESC
        LIMIT 1
        """
        self.cursor.execute(sql, (opponent_name, streamer_picked_race, opponent_name, streamer_picked_race, opponent_name, opp_race, opponent_name, opp_race))
        row = self.cursor.fetchone()

        if row and row['Replay_Summary']:  # Updated this line
            replay_summary = row['Replay_Summary']

            # Find the index of the opponent's build order
            build_order_start = replay_summary.find(
                f"{opponent_name}'s Build Order")

            # If the opponent's build order is not found, return an empty list
            if build_order_start == -1:
                return []

            # Slice the replay summary from the start of the build order
            build_order_section = replay_summary[build_order_start:]

            # Split this section into lines
            build_order_lines = build_order_section.split('\n')

            # remove the Time: entries
            stripped_list = []
            for line in build_order_lines:
                # Split the line based on the comma
                parts = line.split(',', 1)
                if len(parts) > 1:
                    stripped_list.append(parts[1].strip())
                else:
                    stripped_list.append(parts[0])

            reformatted_list = []
            for line in stripped_list:
                match = re.match(r"Name: (\w+), Supply: (\d+)", line)
                if match:
                    reformatted_list.append(
                        f"{match.group(1)} at {match.group(2)}")
                else:
                    reformatted_list.append(line)

            # remove the ' and " characters
            reformatted_list = [line.replace("'", "").replace(
                '"', '') for line in reformatted_list]

            # Extract the first 10 lines (or as many as exist)
            return reformatted_list[1:30]

        else:
            return None

    def test_database(self):

        db = Database()

        # CREATE
        trait_id = db.create_major_trait(("TraitName", "TraitDescription"))
        self.logger.debug(f"Inserted major trait with ID {trait_id}")

        # READ
        self.logger.debug(db.read_major_trait(trait_id))

        # UPDATE
        db.update_major_trait(
            trait_id, ("UpdatedTraitName", "UpdatedTraitDescription"))
        self.logger.debug(f"Updated major trait with ID {trait_id}")
        self.logger.debug(db.read_major_trait(trait_id))

        # DELETE
        # db.delete_major_trait(trait_id)
        # self.logger.debug(f"Deleted major trait with ID {trait_id}")

        # This is a sample test for one table. For testing other tables, you will need
        # to add their CRUD methods and use them in a similar fashion.
        # Also, to test relationships between tables, you will first need to insert
        # data into the parent tables before inserting into child tables.
        # For example, before you can test the PERSONALITY table, you will need to
        # have entries in the MAJOR_TRAITS, MOTIVATIONS, CORE_VALUES, and GOALS tables.

        db.create_user(("Doe", "JohnDoe", "JohnTwitch", "Male", "Male",
                       "1990-01-01", "White", "American", "Engineer", "California", "USA"))
        self.logger.debug(db.read_user(1))
        db.update_user(1, ("Smith", "JohnSmith", "SmithTwitch", "Male", "Male",
                       "1991-01-01", "White", "American", "Engineer", "California", "USA"))
        # db.delete_user(1)

        # db.insert_replay_info()

        db.close()

# TEST


if (config.TEST_MODE):
    # if True:

    # get opponent_name from command line
    opponent_name = input("Enter opponent name: ")
    opp_race = input("Enter opponent race: ")
    streamer_picked_race = input("Enter streamer race: ")        

    result = db.extract_opponent_build_order(opponent_name, opp_race, streamer_picked_race)
    if result:
        # print(", ".join(result).replace(",", "\n", 1))  # CSV in one line
        print(result)
    else:
        print(f"No game found for opponent {opponent_name}.")