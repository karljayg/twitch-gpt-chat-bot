"""
ML Opponent Analyzer - Lightweight version for live game integration

This module provides real-time strategic intelligence about opponents
based on learned patterns from the pattern learning system.
"""

import json
import os
import re
from collections import Counter
from api.chat_utils import processMessageForOpenAI


class MLOpponentAnalyzer:
    def __init__(self):
        self.comments_data = None
        self.patterns_data = None
        self.last_load_time = 0
        self.last_patterns_load_time = 0
        
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
    
    def load_patterns_data(self):
        """Load patterns data with basic caching"""
        try:
            patterns_path = 'data/patterns.json'
            if not os.path.exists(patterns_path):
                return {"patterns": []}
                
            mod_time = os.path.getmtime(patterns_path)
            if self.patterns_data is None or mod_time > self.last_patterns_load_time:
                with open(patterns_path, 'r') as f:
                    self.patterns_data = json.load(f)
                self.last_patterns_load_time = mod_time
                
            return self.patterns_data
        except Exception as e:
            print(f"Error loading patterns data: {e}")
            return {"patterns": []}
    
    def analyze_opponent_for_chat(self, opponent_name, opponent_race, current_map, logger, db=None):
        """
        Analyze opponent and generate chat message if enough data exists
        Enhanced: Falls back to database replay analysis with learned pattern matching
        Returns None if opponent is unknown or insufficient data
        """
        try:
            # Load learning data
            learning_data = self.load_learning_data()
            
            # Find games against this opponent in learning data (commented games)
            opponent_games = [
                comment for comment in learning_data.get('comments', [])
                if comment.get('game_data', {}).get('opponent_name') == opponent_name
            ]
            
            # If we have learning data (commented games), use that
            if opponent_games and len(opponent_games) >= 2:
                return self._analyze_from_learning_data(opponent_games, opponent_name, logger)
            
            # Fallback: Use database replay data with pattern matching
            if db is not None:
                return self._analyze_from_database_with_patterns(opponent_name, opponent_race, db, logger)
            
            # Skip if no data source available
            if logger:
                logger.debug(f"ML Analysis: No historical data for opponent '{opponent_name}' - skipping")
            return None
            
        except Exception as e:
            if logger:
                logger.error(f"Error in ML opponent analysis: {e}")
            return None

    def _analyze_from_learning_data(self, opponent_games, opponent_name, logger):
        """Analyze opponent using learning data (commented games)"""
        try:
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
                'analysis_type': 'learning_data',
                'total_games': total_games,
                'win_rate': win_rate,
                'top_strategies': top_strategies,
                'recent_comments': recent_comments[-3:]  # Last 3 comments
            }
            
            if logger:
                logger.info(f"ML Analysis: Found {total_games} commented games vs {opponent_name}, {win_rate:.1%} win rate")
            
            return analysis_data
            
        except Exception as e:
            if logger:
                logger.error(f"Error analyzing learning data: {e}")
            return None

    def _analyze_from_database_with_patterns(self, opponent_name, opponent_race, db, logger):
        """Analyze opponent using database replays and learned pattern matching"""
        try:
            # Get opponent's replay data from database
            opponent_replay = db.check_player_exists(opponent_name)
            
            if not opponent_replay:
                if logger:
                    logger.debug(f"ML Analysis: No database records for opponent '{opponent_name}'")
                return None
            
            # Extract build order from replay summary
            build_order = self._extract_build_order_from_summary(
                opponent_replay.get('Replay_Summary', ''), opponent_name
            )
            
            if not build_order:
                if logger:
                    logger.debug(f"ML Analysis: No build order data for opponent '{opponent_name}'")
                return None
            
            # Load learned patterns for comparison
            patterns_data = self.load_patterns_data()
            
            # Match opponent's build against learned patterns
            matched_patterns = self._match_build_against_patterns(build_order, patterns_data, logger)
            
            if not matched_patterns:
                if logger:
                    logger.debug(f"ML Analysis: No pattern matches for opponent '{opponent_name}'")
                return None
            
            # Prepare analysis data
            analysis_data = {
                'opponent_name': opponent_name,
                'opponent_race': opponent_race,
                'analysis_type': 'pattern_matching',
                'total_games': 1,  # Only have 1 replay
                'win_rate': 0.0,  # Unknown from single replay
                'matched_patterns': matched_patterns,
                'build_order_preview': build_order[:10]  # First 10 steps
            }
            
            if logger:
                logger.info(f"ML Analysis: Pattern matching analysis for {opponent_name}, {len(matched_patterns)} pattern matches")
            
            return analysis_data
            
        except Exception as e:
            if logger:
                logger.error(f"Error in database pattern analysis: {e}")
            return None

    def _extract_build_order_from_summary(self, replay_summary, player_name):
        """Extract build order data from replay summary for a specific player"""
        try:
            build_order = []
            
            # Split into lines and find the build order section
            lines = replay_summary.split('\n')
            in_build_section = False
            
            for line in lines:
                # Start of this player's build order section
                if f"{player_name}'s Build Order" in line:
                    in_build_section = True
                    continue
                
                # End of this player's build order (another player's section or empty line)
                if in_build_section and (
                    ("'s Build Order" in line and player_name not in line) or
                    line.strip() == ""
                ):
                    break
                
                # Parse build order step
                if in_build_section and "Time:" in line:
                    step_match = re.search(r"Time: (\d+):(\d+), Name: ([^,]+), Supply: (\d+)", line)
                    if step_match:
                        minute, second, unit_name, supply = step_match.groups()
                        time_seconds = int(minute) * 60 + int(second)
                        build_order.append({
                            'supply': int(supply),
                            'name': unit_name.strip(),
                            'time': time_seconds
                        })
            
            return build_order
        except Exception as e:
            return []

    def _match_build_against_patterns(self, build_order, patterns_data, logger):
        """Match opponent's build order against learned patterns"""
        try:
            # Handle different patterns.json structures
            if 'patterns' in patterns_data:
                patterns = patterns_data['patterns']
            else:
                # Extract all pattern_XXX entries
                patterns = [patterns_data[key] for key in patterns_data.keys() if key.startswith('pattern_')]
            
            matched_patterns = []
            
            # Extract unit sequence from build order
            unit_sequence = [step['name'] for step in build_order[:15]]  # First 15 units
            unit_sequence_str = ' '.join(unit_sequence).lower()
            
            # Match against learned patterns using keywords and strategy types
            for pattern in patterns:
                pattern_keywords = pattern.get('keywords', [])
                if not pattern_keywords:
                    continue
                
                # Extract common unit types from opponent's build
                opponent_units = set(unit_sequence_str.split())
                
                # Convert keywords to lowercase for comparison
                pattern_keywords_lower = [kw.lower() for kw in pattern_keywords if isinstance(kw, str)]
                
                # Calculate keyword overlap (unit-based similarity)
                common_keywords = 0
                for unit in opponent_units:
                    if any(unit in kw for kw in pattern_keywords_lower):
                        common_keywords += 1
                
                # Calculate similarity based on keyword overlap
                if len(opponent_units) > 0:
                    similarity_score = common_keywords / len(opponent_units)
                else:
                    similarity_score = 0
                
                if similarity_score > 0.15:  # 15% similarity threshold (more lenient)
                    matched_patterns.append({
                        'comment': pattern.get('comment', 'Unknown strategy'),
                        'keywords': pattern_keywords[:10],  # First 10 keywords
                        'similarity': similarity_score,
                        'strategy_type': pattern.get('strategy_type', 'unknown'),
                        'race': pattern.get('race', 'unknown')
                    })
            
            # Sort by similarity
            matched_patterns.sort(key=lambda x: x['similarity'], reverse=True)
            
            return matched_patterns[:3]  # Top 3 matches
            
        except Exception as e:
            if logger:
                logger.error(f"Error matching patterns: {e}")
            return []

    def _calculate_sequence_similarity(self, seq1, seq2):
        """Calculate similarity between two unit sequences"""
        if not seq1 or not seq2:
            return 0.0
        
        # Simple approach: count common units
        units1 = set(seq1.split())
        units2 = set(seq2.split())
        
        if not units1 or not units2:
            return 0.0
        
        common_units = len(units1.intersection(units2))
        total_units = len(units1.union(units2))
        
        return common_units / total_units if total_units > 0 else 0.0
    
    def generate_ml_analysis_message(self, analysis_data, twitch_bot, logger, contextHistory):
        """
        Generate ML analysis message via OpenAI and send to chat
        """
        try:
            # Build prompt for OpenAI based on analysis type
            data = analysis_data
            analysis_type = data.get('analysis_type', 'learning_data')
            
            msg = "Generate a concise ML analysis for Twitch chat based on opponent data. "
            msg += "Keep it under 200 characters and strategic. "
            msg += "Format: 'ML Analysis: [your analysis]'\n\n"
            msg += f"Opponent: {data['opponent_name']}\n"
            
            if analysis_type == 'learning_data':
                # Analysis based on commented games
                msg += f"Historical record: {data['total_games']} games, {data['win_rate']:.0%} win rate\n"
                
                if data.get('top_strategies'):
                    msg += "Common strategies: "
                    strategies = [strategy for strategy, count in data['top_strategies'][:3]]
                    msg += ", ".join(strategies) + "\n"
                
                if data.get('recent_comments'):
                    msg += "Recent game notes:\n"
                    for comment in data['recent_comments']:
                        msg += f"- {comment[:100]}\n"
            
            elif analysis_type == 'pattern_matching':
                # Analysis based on pattern matching
                msg += f"Build pattern analysis (vs learned strategies):\n"
                
                if data.get('matched_patterns'):
                    msg += "Similar to learned patterns:\n"
                    for pattern in data['matched_patterns'][:2]:
                        similarity = pattern['similarity'] * 100
                        msg += f"- {pattern['comment']} ({similarity:.0f}% match)\n"
                        if pattern.get('keywords'):
                            keywords = ", ".join(pattern['keywords'][:3])
                            msg += f"  Keywords: {keywords}\n"
                
                if data.get('build_order_preview'):
                    build_preview = [step['name'] for step in data['build_order_preview'][:5]]
                    msg += f"Opening: {' → '.join(build_preview)}\n"
            
            msg += "\nGenerate strategic advice for chat viewers about this opponent based on the analysis."
            
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
        twitch_bot: TwitchBot instance (has .db attribute) for chat output and database access
        logger: Logger instance
        contextHistory: Chat context history
    
    Returns:
        True if analysis was generated, False if skipped
    """
    try:
        analyzer = get_ml_analyzer()
        
        # Analyze opponent (enhanced with database fallback)
        db_instance = getattr(twitch_bot, 'db', None)
        analysis_data = analyzer.analyze_opponent_for_chat(
            opponent_name, opponent_race, current_map, logger, db_instance
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
