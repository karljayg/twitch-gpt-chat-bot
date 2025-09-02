#!/usr/bin/env python3
"""
ML Opponent Analyzer - Enhanced version with priority system for player comments
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
        self._current_opponent_comment = None  # Store current opponent's comment for priority
        
    def load_learning_data(self):
        """Load comments data with basic caching"""
        try:
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
            
            # Store the opponent's comment for priority matching
            self._current_opponent_comment = opponent_replay.get('Player_Comments', '')
            
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
            matched_patterns = self._match_build_against_patterns(build_order, patterns_data, opponent_race, logger)
            
            if not matched_patterns:
                if logger:
                    logger.debug(f"ML Analysis: No pattern matches for opponent '{opponent_name}'")
                return None
            
            # Generate concise summary instead of raw data
            summary = self._generate_concise_summary(opponent_name, opponent_race, matched_patterns, build_order)
            
            # Prepare analysis data
            analysis_data = {
                'opponent_name': opponent_name,
                'opponent_race': opponent_race,
                'analysis_type': 'pattern_matching',
                'total_games': 1,  # Only have 1 replay
                'win_rate': 0.0,  # Unknown from single replay
                'matched_patterns': matched_patterns,
                'summary': summary
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
                # Start of this player's build order section (case-insensitive)
                if f"{player_name}'s Build Order".lower() in line.lower():
                    in_build_section = True
                    continue
                
                # End of this player's build order (another player's section or empty line)
                if in_build_section and (
                    ("'s Build Order" in line and player_name.lower() not in line.lower()) or
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

    def _match_build_against_patterns(self, build_order, patterns_data, opponent_race, logger):
        """Match opponent's build order against learned patterns with priority for player comments"""
        if logger:
            logger.debug(f"Pattern matching for opponent race: {opponent_race}")
        try:
            # Handle different patterns.json structures
            if 'patterns' in patterns_data:
                patterns = patterns_data['patterns']
            else:
                # Extract all pattern_XXX entries
                patterns = [patterns_data[key] for key in patterns_data.keys() if key.startswith('pattern_')]
            
            matched_patterns = []
            
            # Extract complete build order sequence (units AND buildings)
            unit_sequence = [step['name'] for step in build_order]  # ALL items to catch any strategic elements
            unit_sequence_str = ' '.join(unit_sequence).lower()
            
            # Match against learned patterns using keywords and strategy types
            for pattern in patterns:
                pattern_keywords = pattern.get('keywords', [])
                if not pattern_keywords:
                    continue
                
                # Skip overly generic patterns that dominate results
                comment = pattern.get('comment', '').lower()
                generic_indicators = ['hello world', 'first comment', 'test', 'computer']
                if any(indicator in comment for indicator in generic_indicators):
                    continue
                
                # Filter patterns by race relevance - check if pattern contains race-specific units
                pattern_race = self._determine_pattern_race(pattern_keywords)
                opponent_race_lower = opponent_race.lower() if opponent_race else 'unknown'
                
                # Additional comment-based race filtering using existing race unit lists
                comment_race = self._determine_pattern_race_from_comment(pattern.get('comment', ''))
                if comment_race != 'unknown' and comment_race != opponent_race_lower:
                    if logger:
                        logger.debug(f"Pattern '{pattern.get('comment', '')}' filtered out by comment race: {comment_race} != {opponent_race_lower}")
                    continue
                
                # Original race filtering logic
                if pattern_race and pattern_race != 'unknown':
                    if pattern_race != opponent_race_lower:
                        if logger:
                            logger.debug(f"Pattern '{pattern.get('comment', '')}' filtered out by pattern race: {pattern_race} != {opponent_race_lower}")
                        continue
                
                # Extract common unit types from opponent's build
                opponent_units = set(unit_sequence_str.split())
                
                # Convert keywords to lowercase for comparison
                pattern_keywords_lower = [kw.lower() for kw in pattern_keywords if isinstance(kw, str)]
                
                # Get strategic keywords from actual player comments in database
                strategic_keywords = self._get_strategic_keywords_from_comments()
                
                # Calculate keyword overlap with strategic weighting
                common_keywords = 0
                strategic_matches = 0
                
                for unit in opponent_units:
                    matched = False
                    for kw in pattern_keywords_lower:
                        if unit in kw or kw in unit:
                            common_keywords += 1
                            # Give extra weight for strategic keywords
                            if kw in strategic_keywords:
                                strategic_matches += 1
                            matched = True
                            break
                
                # Calculate similarity with strategic weighting
                if len(opponent_units) > 0:
                    base_similarity = common_keywords / len(opponent_units)
                    strategic_bonus = strategic_matches * 0.1  # 10% bonus per strategic match
                    similarity_score = base_similarity + strategic_bonus
                else:
                    similarity_score = 0
                
                # PRIORITY BOOST: Give massive bonus to patterns that match the opponent's actual comment
                # This ensures player comments take absolute priority
                comment_priority_boost = 0.0
                if self._current_opponent_comment:
                    opponent_comment_lower = self._current_opponent_comment.lower()
                    pattern_comment_lower = pattern.get('comment', '').lower()
                    
                    # Check for exact or very close comment matches
                    if pattern_comment_lower == opponent_comment_lower:
                        comment_priority_boost = 1.0  # 100% bonus for exact match
                        if logger:
                            logger.debug(f"EXACT COMMENT MATCH: '{pattern_comment_lower}' = '{opponent_comment_lower}' - +1.0 boost")
                    elif any(keyword in opponent_comment_lower for keyword in pattern_keywords_lower):
                        comment_priority_boost = 0.5  # 50% bonus for keyword overlap
                        if logger:
                            logger.debug(f"KEYWORD OVERLAP: '{pattern_keywords_lower}' in '{opponent_comment_lower}' - +0.5 boost")
                    elif any(keyword in pattern_comment_lower for keyword in opponent_comment_lower.split()):
                        comment_priority_boost = 0.3  # 30% bonus for reverse keyword match
                        if logger:
                            logger.debug(f"REVERSE KEYWORD MATCH: '{opponent_comment_lower.split()}' in '{pattern_comment_lower}' - +0.3 boost")
                
                # Apply comment priority boost
                similarity_score += comment_priority_boost
                if logger and comment_priority_boost > 0:
                    logger.debug(f"Pattern '{pattern.get('comment', '')}' got +{comment_priority_boost} boost, final score: {similarity_score}")
                
                # No artificial strategic conflict filtering - let pattern matching work naturally
                # based on what actually exists in the build order and player comments
                
                if similarity_score > 0.05:  # 5% similarity threshold (more lenient for strategic patterns like DT)
                    matched_patterns.append({
                        'comment': pattern.get('comment', 'Unknown strategy'),
                        'keywords': pattern_keywords[:10],  # First 10 keywords
                        'similarity': similarity_score,
                        'strategy_type': pattern.get('strategy_type', 'unknown'),
                        'race': pattern.get('race', 'unknown')
                    })
            
            # Sort by similarity (highest first)
            matched_patterns.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Debug: Log the top patterns after sorting
            if logger:
                logger.debug(f"Top patterns after sorting:")
                for i, pattern in enumerate(matched_patterns[:5]):
                    logger.debug(f"  {i+1}. '{pattern['comment']}' - Score: {pattern['similarity']:.4f}")
            
            return matched_patterns[:3]  # Top 3 matches
            
        except Exception as e:
            if logger:
                logger.error(f"Error matching patterns: {e}")
            return []

    def _generate_concise_summary(self, opponent_name, opponent_race, matched_patterns, build_order):
        """Generate a concise, readable summary for chat"""
        try:
            # Get the top pattern (highest priority)
            top_pattern = matched_patterns[0] if matched_patterns else None
            
            if not top_pattern:
                return f"ML Analysis: {opponent_name} ({opponent_race}) - No strategic patterns detected"
            
            # Extract key strategic elements from build order
            strategic_elements = []
            for step in build_order[:15]:  # First 15 steps for opening
                unit = step['name'].lower()
                if any(keyword in unit for keyword in ['forge', 'cannon', 'darkshrine', 'templar', 'robo', 'stargate']):
                    strategic_elements.append(step['name'])
            
            # Build the summary
            summary_parts = [f"ML Analysis: {opponent_name} ({opponent_race})"]
            
            if strategic_elements:
                summary_parts.append(f"Build: {' → '.join(strategic_elements[:3])}")
            
            if top_pattern:
                comment = top_pattern['comment']
                similarity = top_pattern['similarity']
                if similarity > 0.5:  # High confidence
                    summary_parts.append(f"Strategy: {comment}")
                else:
                    summary_parts.append(f"Similar to: {comment}")
            
            return " - ".join(summary_parts)
            
        except Exception as e:
            return f"ML Analysis: {opponent_name} ({opponent_race}) - Analysis available"

    def _get_strategic_keywords_from_comments(self):
        """Extract strategic keywords from all player comments in database"""
        try:
            # Common non-strategic words to filter out
            common_words = {
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'a', 'an', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
                'we', 'they', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
                'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may',
                'then', 'into', 'after', 'vs', 'game', 'player', 'build', 'order', 'base',
                'first', 'second', 'early', 'late', 'quick', 'fast', 'slow', 'good', 'bad',
                'big', 'small', 'new', 'old', 'high', 'low', 'long', 'short', 'much', 'many',
                'some', 'any', 'all', 'no', 'not', 'very', 'too', 'so', 'just', 'only', 'also'
            }
            
            # Extract all unique words from player comments
            strategic_keywords = set()
            
            # Get player comments from patterns data
            patterns_data = self.load_patterns_data()
            if patterns_data:
                pattern_list = [patterns_data[key] for key in patterns_data.keys() if key.startswith('pattern_')]
                
                for pattern in pattern_list:
                    comment = pattern.get('comment', '')
                    if comment and len(comment) > 10:  # Skip very short comments
                        # Extract words from comment, clean and filter
                        words = comment.lower().replace(',', ' ').replace('.', ' ').split()
                        for word in words:
                            # Clean word and filter
                            word = word.strip('.,!?()[]{}":;')
                            if (len(word) >= 3 and  # At least 3 characters
                                word.isalpha() and  # Only alphabetic
                                word not in common_words):  # Not a common word
                                strategic_keywords.add(word)
            
            return list(strategic_keywords)
            
        except Exception as e:
            # Fallback to basic strategic keywords if extraction fails
            return ['cannon', 'rush', 'drop', 'proxy', 'timing', 'pressure', 'allin']

    def _get_race_units(self):
        """Get race-specific units and buildings from comprehensive JSON reference"""
        try:
            import json
            import os
            
            # Load the comprehensive SC2 race data
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sc2_race_data.json')
            with open(json_path, 'r') as f:
                race_data = json.load(f)
            
            # Combine all categories for each race and normalize to lowercase
            race_units = {}
            for race_name, race_info in race_data.items():
                race_key = race_name.lower()
                race_units[race_key] = set()
                
                # Add all units, buildings, spells/abilities, upgrades, and terminology
                for category in ['Units', 'Buildings', 'Spells/Abilities', 'Upgrades', 'Terminology']:
                    if category in race_info:
                        for item in race_info[category]:
                            # Normalize item to lowercase and remove spaces/special chars for matching
                            normalized = item.lower().replace(' ', '').replace('-', '').replace('/', '').replace('(', '').replace(')', '').replace(':', '')
                            race_units[race_key].add(normalized)
                            
                            # Also add individual words for better matching
                            words = item.lower().split()
                            for word in words:
                                clean_word = word.replace('(', '').replace(')', '').replace(',', '').replace(':', '')
                                if len(clean_word) >= 3:  # Only add meaningful words
                                    race_units[race_key].add(clean_word)
            
            return race_units
            
        except Exception as e:
            # Fallback to basic units if JSON loading fails
            return {
                'protoss': {'probe', 'zealot', 'stalker', 'cannon', 'templar', 'dark', 'shrine'},
                'terran': {'scv', 'marine', 'reaper', 'mech', 'rax', 'banshee'},
                'zerg': {'drone', 'zergling', 'banes', 'speedling', 'ling'}
            }

    def _determine_pattern_race(self, pattern_keywords):
        """Determine the race of a pattern based on its keywords"""
        if not pattern_keywords:
            return 'unknown'
        
        race_units = self._get_race_units()
        
        # Convert keywords to lowercase and remove duplicates (fix for corrupted patterns)
        keywords_lower = list(set([kw.lower() for kw in pattern_keywords if isinstance(kw, str)]))
        
        # Count race-specific matches using unique keywords only
        race_matches = {}
        for race, units in race_units.items():
            unique_matches = set()
            for keyword in keywords_lower:
                if keyword in units:
                    unique_matches.add(keyword)
            race_matches[race] = len(unique_matches)
        
        # Return the race with the most matches, or 'unknown' if no clear winner
        max_matches = max(race_matches.values())
        if max_matches == 0:
            return 'unknown'
        
        # Find race(s) with max matches
        best_races = [race for race, matches in race_matches.items() if matches == max_matches]
        
        # If there's a tie, return 'unknown' to be safe
        if len(best_races) > 1:
            return 'unknown'
        
        return best_races[0]

    def _determine_pattern_race_from_comment(self, comment):
        """Determine race from pattern comment text using same race unit lists"""
        if not comment:
            return 'unknown'
        
        race_units = self._get_race_units()
        
        comment_lower = comment.lower()
        
        # Count race-specific matches in comment
        race_matches = {}
        for race, units in race_units.items():
            matches = 0
            for unit in units:
                if unit in comment_lower:
                    matches += 1
            race_matches[race] = matches
        
        # Return the race with the most matches, or 'unknown' if no clear winner
        max_matches = max(race_matches.values())
        if max_matches == 0:
            return 'unknown'
        
        # Find race(s) with max matches
        best_races = [race for race, matches in race_matches.items() if matches == max_matches]
        
        # If there's a tie, return 'unknown' to be safe
        if len(best_races) > 1:
            return 'unknown'
        
        return best_races[0]

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


def get_ml_analyzer():
    """Get or create ML analyzer instance"""
    return MLOpponentAnalyzer()


def analyze_opponent_for_game_start(opponent_name, opponent_race, current_map, twitch_bot, logger, contextHistory):
    """
    Analyze opponent at game start and send ML analysis to chat
    """
    try:
        analyzer = get_ml_analyzer()
        
        # Analyze opponent (enhanced with database fallback)
        db_instance = getattr(twitch_bot, 'db', None)
        analysis_data = analyzer.analyze_opponent_for_chat(
            opponent_name, opponent_race, current_map, logger, db_instance
        )
        
        if analysis_data:
            # Generate and send ML analysis message
            analyzer.generate_ml_analysis_message(analysis_data, twitch_bot, logger, contextHistory)
            return True
        else:
            return False
            
    except Exception as e:
        if logger:
            logger.error(f"Error in game start ML analysis: {e}")
        return False
