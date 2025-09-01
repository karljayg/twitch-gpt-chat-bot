"""
ML Opponent Analyzer - Lightweight version for live game integration

This module provides real-time strategic intelligence about opponents
based on learned patterns from the pattern learning system.
"""

import json
import os
from collections import Counter
from api.chat_utils import processMessageForOpenAI


class MLOpponentAnalyzer:
    def __init__(self):
        self.comments_data = None
        self.last_load_time = 0
        
    def load_learning_data(self):
        """Load comments data with basic caching"""
        try:
            # Simple file modification check for caching
            comments_path = 'data/comments.json'
            if not os.path.exists(comments_path):
                return {"comments": [], "keyword_index": {}}
                
            mod_time = os.path.getmtime(comments_path)
            if self.comments_data is None or mod_time > self.last_load_time:
                with open(comments_path, 'r') as f:
                    self.comments_data = json.load(f)
                self.last_load_time = mod_time
                
            return self.comments_data
        except Exception as e:
            print(f"Error loading ML learning data: {e}")
            return {"comments": [], "keyword_index": {}}
    
    def analyze_opponent_for_chat(self, opponent_name, opponent_race, current_map, logger):
        """
        Analyze opponent and generate chat message if enough data exists
        Returns None if opponent is unknown or insufficient data
        """
        try:
            # Load learning data
            learning_data = self.load_learning_data()
            
            # Find games against this opponent
            opponent_games = [
                comment for comment in learning_data.get('comments', [])
                if comment.get('game_data', {}).get('opponent_name') == opponent_name
            ]
            
            # Skip if no historical data
            if not opponent_games:
                if logger:
                    logger.debug(f"ML Analysis: No historical data for opponent '{opponent_name}' - skipping")
                return None
            
            # Skip if insufficient data (less than 2 games)
            if len(opponent_games) < 2:
                if logger:
                    logger.debug(f"ML Analysis: Insufficient data for opponent '{opponent_name}' ({len(opponent_games)} games) - skipping")
                return None
            
            # Calculate basic statistics
            total_games = len(opponent_games)
            wins = sum(1 for game in opponent_games if game.get('game_data', {}).get('result') == 'Victory')
            win_rate = wins / total_games if total_games > 0 else 0
            
            # Extract strategic keywords
            all_keywords = []
            recent_comments = []
            
            for game in opponent_games:
                all_keywords.extend(game.get('keywords', []))
                recent_comments.append(game.get('comment', ''))
            
            # Get most common strategic themes
            keyword_frequency = Counter(all_keywords)
            top_strategies = keyword_frequency.most_common(5)
            
            # Prepare data for OpenAI summary
            analysis_data = {
                'opponent_name': opponent_name,
                'opponent_race': opponent_race,
                'total_games': total_games,
                'win_rate': win_rate,
                'top_strategies': top_strategies,
                'recent_comments': recent_comments[-3:]  # Last 3 comments
            }
            
            if logger:
                logger.info(f"ML Analysis: Found {total_games} games vs {opponent_name}, {win_rate:.1%} win rate")
            
            return analysis_data
            
        except Exception as e:
            if logger:
                logger.error(f"Error in ML opponent analysis: {e}")
            return None
    
    def generate_ml_analysis_message(self, analysis_data, twitch_bot, logger, contextHistory):
        """
        Generate ML analysis message via OpenAI and send to chat
        """
        try:
            # Build prompt for OpenAI
            data = analysis_data
            msg = "Generate a concise ML analysis for Twitch chat based on opponent data. "
            msg += "Keep it under 200 characters and strategic. "
            msg += "Format: 'ML Analysis: [your analysis]'\n\n"
            msg += f"Opponent: {data['opponent_name']} ({data['opponent_race']})\n"
            msg += f"Historical record: {data['total_games']} games, {data['win_rate']:.0%} win rate\n"
            
            if data['top_strategies']:
                msg += "Common strategies: "
                strategies = [strategy for strategy, count in data['top_strategies'][:3]]
                msg += ", ".join(strategies) + "\n"
            
            if data['recent_comments']:
                msg += "Recent game notes:\n"
                for comment in data['recent_comments']:
                    msg += f"- {comment[:100]}\n"
            
            msg += "\nGenerate strategic advice for chat viewers about this opponent."
            
            # Send to OpenAI for natural language generation
            if logger:
                logger.debug(f"Sending ML analysis prompt to OpenAI for opponent: {data['opponent_name']}")
            processMessageForOpenAI(twitch_bot, msg, "ml_analysis", logger, contextHistory)
            
        except Exception as e:
            if logger:
                logger.error(f"Error generating ML analysis message: {e}")


# Global instance for efficiency
_ml_analyzer = None

def get_ml_analyzer():
    """Get or create the global ML analyzer instance"""
    global _ml_analyzer
    if _ml_analyzer is None:
        _ml_analyzer = MLOpponentAnalyzer()
    return _ml_analyzer


def analyze_opponent_for_game_start(opponent_name, opponent_race, current_map, twitch_bot, logger, contextHistory):
    """
    Main entry point for ML opponent analysis during game start
    
    Args:
        opponent_name: Name of the opponent
        opponent_race: Race of the opponent  
        current_map: Current map name
        twitch_bot: TwitchBot instance for chat output
        logger: Logger instance
        contextHistory: Chat context history
    
    Returns:
        True if analysis was generated, False if skipped
    """
    try:
        analyzer = get_ml_analyzer()
        
        # Analyze opponent
        analysis_data = analyzer.analyze_opponent_for_chat(
            opponent_name, opponent_race, current_map, logger
        )
        
        # If no data or insufficient data, skip silently
        if analysis_data is None:
            return False
        
        # Generate and send ML analysis message
        analyzer.generate_ml_analysis_message(
            analysis_data, twitch_bot, logger, contextHistory
        )
        
        if logger:
            logger.info(f"ML Analysis sent to chat for opponent: {opponent_name}")
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error in ML opponent analysis: {e}")
        return False
