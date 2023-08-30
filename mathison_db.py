import mysql.connector
import re
import logging
import datetime
import pytz
from settings import config

class Database:
    def __init__(self):

        #logger = logging.getLogger("bot")

        self.connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        self.cursor = self.connection.cursor()      

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
            # Define the query
            query = """
                SELECT Replay_Summary 
                FROM Replays 
                WHERE (Player1_Id = (SELECT Id FROM Players WHERE SC2_UserId = %s) AND Player1_Race = %s) 
                OR (Player2_Id = (SELECT Id FROM Players WHERE SC2_UserId = %s) AND Player2_Race = %s);
            """

            # Execute the query
            self.cursor.execute(query, (player_name, player_race, player_name, player_race))
            
            # Fetch the result
            result = self.cursor.fetchone()

            # Return the replay summary if found, else None
            if result:
                return result[0]
            return None
        except Exception as e:
            #logger.error(f"Error checking if player exists: {e}")
            print(f"Error checking if player exists: {e}")
            return None


    def insert_replay_info(self, replay_summary):
        # The replay summary
        #with open("temp/replay_summary.txt", "r") as file:
        #    replay_summary = file.read()

        # Extract details using regex
        player_matches = re.search(r"Players: (\w+): (\w+), (\w+): (\w+)", replay_summary)
        winners_matches = re.search(r"Winners: (\w+)", replay_summary)
        losers_matches = re.search(r"Losers: (\w+)", replay_summary)
        map_match = re.search(r"Map: (.+?)\n", replay_summary)
        game_duration_match = re.search(r"Game Duration: (.+?)\n", replay_summary)
        game_type_match = re.search(r"Game Type: (\w+)", replay_summary)
        region_match = re.search(r"Region: (\w+)", replay_summary)
        timestamp_match = re.search(r'Timestamp:\s*(\d+)', replay_summary)

        # Extracted details
        player1_name, player1_race, player2_name, player2_race = player_matches.groups()
        winner = winners_matches.group(1)
        loser = losers_matches.group(1)
        game_map = map_match.group(1)
        game_duration = game_duration_match.group(1)
        game_type = game_type_match.group(1)
        region = region_match.group(1)
        timestamp = timestamp_match.group(1)

        # Check if UnixTimestamp already exists
        self.cursor.execute("SELECT 1 FROM Replays WHERE UnixTimestamp = %s", (timestamp,))
        existing_entry = self.cursor.fetchone()

        # Convert the Unix timestamp to US Eastern time
        utc_dt = datetime.datetime.utcfromtimestamp(int(timestamp))
        eastern = pytz.timezone('US/Eastern')
        utc_dt = pytz.utc.localize(utc_dt)
        eastern_dt = utc_dt.astimezone(eastern)
        date_played = eastern_dt.strftime('%Y-%m-%d %H:%M:%S')        

        if existing_entry:
            #self.logger.debug(f"Entry with UnixTimestamp {timestamp} already exists in the database.")
            print(f"Entry with UnixTimestamp {timestamp} already exists in the database.")
            return

        # Insert players into the Players table
        for player, race in [(player1_name, player1_race), (player2_name, player2_race)]:
            self.cursor.execute("INSERT IGNORE INTO Players (Id, SC2_UserId) VALUES (NULL, %s)", (player,))

        # Retrieve player IDs
        self.cursor.execute("SELECT Id FROM Players WHERE SC2_UserId = %s", (player1_name,))
        player1_id = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT Id FROM Players WHERE SC2_UserId = %s", (player2_name,))
        player2_id = self.cursor.fetchone()[0]

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

    def test_database():

        db = Database()

        # CREATE
        trait_id = db.create_major_trait(("TraitName", "TraitDescription"))
        print(f"Inserted major trait with ID {trait_id}")

        # READ
        print(db.read_major_trait(trait_id))

        # UPDATE
        db.update_major_trait(trait_id, ("UpdatedTraitName", "UpdatedTraitDescription"))
        print(f"Updated major trait with ID {trait_id}")
        print(db.read_major_trait(trait_id))

        # DELETE
        #db.delete_major_trait(trait_id)
        #print(f"Deleted major trait with ID {trait_id}")

        # This is a sample test for one table. For testing other tables, you will need
        # to add their CRUD methods and use them in a similar fashion.
        # Also, to test relationships between tables, you will first need to insert
        # data into the parent tables before inserting into child tables.
        # For example, before you can test the PERSONALITY table, you will need to
        # have entries in the MAJOR_TRAITS, MOTIVATIONS, CORE_VALUES, and GOALS tables.

        db.create_user(("Doe", "JohnDoe", "JohnTwitch", "Male", "Male", "1990-01-01", "White", "American", "Engineer", "California", "USA"))
        print(db.read_user(1))
        db.update_user(1, ("Smith", "JohnSmith", "SmithTwitch", "Male", "Male", "1991-01-01", "White", "American", "Engineer", "California", "USA"))
        # db.delete_user(1)

        #db.insert_replay_info()

        db.close()
