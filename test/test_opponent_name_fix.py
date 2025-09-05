import unittest
import tempfile
import shutil
import os
import sys

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.twitch_bot import TwitchBot
from settings import config


class TestOpponentNameExtraction(unittest.TestCase):
    """Test that opponent names are extracted correctly from comma-separated strings"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_dir = config.PATTERN_DATA_DIR
        config.PATTERN_DATA_DIR = self.temp_dir
        
        # Create a mock TwitchBot instance
        self.bot = TwitchBot()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
        config.PATTERN_DATA_DIR = self.original_data_dir
        
    def test_opponent_name_extraction_muskul(self):
        """Test that 'Muskul, KJ' extracts 'Muskul' as opponent"""
        game_player_names = "Muskul, KJ"
        winning_players = "KJ"
        losing_players = "Muskul"
        
        game_data = self.bot._prepare_game_data_for_comment(
            game_player_names, winning_players, losing_players, None
        )
        
        self.assertEqual(game_data['opponent_name'], 'Muskul')
        
    def test_opponent_name_extraction_egaliza(self):
        """Test that 'KJ, eGaliza' extracts 'eGaliza' as opponent"""
        game_player_names = "KJ, eGaliza"
        winning_players = "eGaliza"
        losing_players = "KJ"
        
        game_data = self.bot._prepare_game_data_for_comment(
            game_player_names, winning_players, losing_players, None
        )
        
        self.assertEqual(game_data['opponent_name'], 'eGaliza')
        
    def test_opponent_name_extraction_heavy(self):
        """Test that 'Heavy, KJ' extracts 'Heavy' as opponent"""
        game_player_names = "Heavy, KJ"
        winning_players = "Heavy"
        losing_players = "KJ"
        
        game_data = self.bot._prepare_game_data_for_comment(
            game_player_names, winning_players, losing_players, None
        )
        
        self.assertEqual(game_data['opponent_name'], 'Heavy')


if __name__ == '__main__':
    unittest.main()

