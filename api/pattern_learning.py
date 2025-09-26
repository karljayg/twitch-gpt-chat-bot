#!/usr/bin/env python3

import json
import re
import os
from datetime import datetime
from collections import defaultdict
import logging

from settings import config

class SC2PatternLearner:
    def __init__(self, db, logger, data_dir=None):
        self.db = db
        self.logger = logger
        self.patterns = defaultdict(list)
        self.comment_keywords = defaultdict(list)
        
        # Use provided data directory or default from config
        self.data_dir = data_dir if data_dir else config.PATTERN_DATA_DIR
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing patterns from file
        self.load_patterns_from_file()
        self.logger.info(f"Pattern learning system initialized with {self.get_total_patterns()} patterns")
        
    def prompt_for_player_comment(self, game_data):
        """
        Gracefully prompt for player comment after game ends
        """
        try:
            # Check if we've already processed this game (prevents duplicate prompts when watching replays)
            game_id = self._generate_game_id(game_data)
            if self._is_game_already_processed(game_id):
                self.logger.info(f"Game already processed (ID: {game_id}), skipping comment prompt")
                return None
            
            # Display game summary and prompt for comment
            game_summary = self._format_game_summary(game_data)
            print("\n" + "="*60)
            print("🎮 GAME COMPLETED - ENTER PLAYER COMMENT")
            print("="*60)
            print(game_summary)
            print("="*60)
            
            # Try to get player input with timeout
            print("Enter player comment about the game (or press Enter to skip)")
            print(f"Timeout: {config.PLAYER_COMMENT_TIMEOUT_SECONDS} seconds...")
            try:
                comment = self._get_input_with_timeout("Comment: ", config.PLAYER_COMMENT_TIMEOUT_SECONDS)
                if comment is not None:
                    comment = comment.strip()
            except (EOFError, OSError, KeyboardInterrupt):
                # If input() fails (common in Twitch bot context), auto-process
                self.logger.info(f"Input not available - auto-processing game for {game_data.get('opponent_name', 'Unknown')} on {game_data.get('map', 'Unknown')}")
                self.process_game_without_comment(game_data)
                return "auto_processed"
            
            if comment:
                # Process the comment
                self._process_new_comment(game_data, comment)
                self.logger.info(f"Player comment received: {comment}")
                return comment
            else:
                # No comment provided (timeout or empty input) - skip processing
                if comment is None:
                    self.logger.info(f"Comment prompt timed out - skipping pattern learning for {game_data.get('opponent_name', 'Unknown')} on {game_data.get('map', 'Unknown')}")
                else:
                    self.logger.info(f"No comment provided - skipping pattern learning for {game_data.get('opponent_name', 'Unknown')} on {game_data.get('map', 'Unknown')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in comment prompt: {e}")
            return None
    
    def add_player_comment_later(self, opponent_name, map_name, date, comment):
        """
        Add a player comment for a game that was already processed
        Useful for adding insights after the fact
        """
        try:
            # Find the game in our processed data
            game_data = self._find_game_by_details(opponent_name, map_name, date)
            
            if game_data:
                self.logger.info(f"Found game vs {opponent_name} on {map_name} - adding comment: {comment}")
                
                # Process the comment
                self._process_new_comment(game_data, comment)
                
                # Update the existing AI pattern with player comment
                self._upgrade_ai_pattern_to_player_comment(game_data, comment)
                
                # Save updated patterns
                self.save_patterns_to_file()
                
                return True
            else:
                self.logger.warning(f"Could not find game vs {opponent_name} on {map_name} around {date}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding player comment later: {e}")
            return False
    
    def edit_ai_comment(self, opponent_name, map_name, date, new_comment):
        """
        Replace an AI-generated comment with a player comment
        This upgrades the pattern from AI-learned to expert insight
        """
        try:
            # Find the game in our processed data
            game_data = self._find_game_by_details(opponent_name, map_name, date)
            
            if game_data:
                self.logger.info(f"Found game vs {opponent_name} on {map_name} - upgrading AI comment to: {new_comment}")
                
                # Process the new comment
                self._process_new_comment(game_data, new_comment)
                
                # Remove the old AI pattern and replace with player comment
                self._replace_ai_pattern_with_player_comment(game_data, new_comment)
                
                # Save updated patterns
                self.save_patterns_to_file()
                
                return True
            else:
                self.logger.warning(f"Could not find game vs {opponent_name} on {map_name} around {date}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error editing AI comment: {e}")
            return False
    
    def list_recent_games_for_comment(self, limit=10):
        """
        List recent games that could benefit from player comments
        Shows games that only have AI-generated patterns
        """
        try:
            recent_games = []
            
            if hasattr(self, 'all_patterns'):
                for pattern in self.all_patterns:
                    if not pattern.get('has_player_comment', False):  # Only AI-generated patterns
                        game_data = pattern.get('game_data', {})
                        if game_data:
                            recent_games.append({
                                'opponent': game_data.get('opponent_name', 'Unknown'),
                                'race': game_data.get('opponent_race', 'Unknown'),
                                'map': game_data.get('map', 'Unknown'),
                                'date': game_data.get('date', 'Unknown'),
                                'ai_comment': pattern.get('comment', 'Unknown'),
                                'confidence': pattern.get('ai_confidence', 0.0)
                            })
            
            # Sort by date (most recent first) and limit results
            recent_games.sort(key=lambda x: x['date'], reverse=True)
            return recent_games[:limit]
            
        except Exception as e:
            self.logger.error(f"Error listing recent games: {e}")
            return []
    
    def _format_game_summary(self, game_data):
        """Format game details for the comment prompt"""
        summary = []
        
        # Basic game info
        if 'opponent_name' in game_data:
            summary.append(f"Opponent: {game_data['opponent_name']}")
        if 'opponent_race' in game_data:
            summary.append(f"Race: {game_data['opponent_race']}")
        if 'result' in game_data:
            summary.append(f"Result: {game_data['result']}")
        if 'map' in game_data:
            summary.append(f"Map: {game_data['map']}")
        if 'duration' in game_data:
            summary.append(f"Duration: {game_data['duration']}")
        if 'date' in game_data:
            summary.append(f"Date: {game_data['date']}")
            
        # Add any additional context
        if 'build_order_summary' in game_data:
            summary.append(f"Build: {game_data['build_order_summary'][:100]}...")
            
        return "\n".join(summary)
    
    def _process_new_comment(self, game_data, comment):
        """Process new comment and update learning system"""
        try:
            # Extract keywords from comment
            keywords = self._extract_keywords(comment)
            
            # Store comment with game data for learning (dual storage)
            comment_data = {
                'raw_comment': comment,  # Original comment as entered
                'cleaned_comment': self._clean_comment_text(comment),  # Cleaned version for analysis
                'comment': comment,  # Keep for backward compatibility
                'keywords': keywords,
                'game_data': game_data,
                'timestamp': datetime.now().isoformat(),
                'has_player_comment': True  # Mark as having expert insight
            }
            
            # Save to database FIRST (this should always happen)
            self._save_comment_to_db(game_data, comment)
            
            # Update keyword patterns and analyze for new patterns (only if keywords found)
            if keywords:
                # Store comment data for each keyword
                for keyword in keywords:
                    self.comment_keywords[keyword].append(comment_data)
                
                # Create pattern ONCE and reference it by all keywords
                self._create_pattern_for_comment(comment_data)
                
                # Save patterns to file for persistence
                self.save_patterns_to_file()
            
            self.logger.info(f"Processed new comment with keywords: {keywords}")
            
        except Exception as e:
            self.logger.error(f"Error processing comment: {e}")
    
    def process_game_without_comment(self, game_data):
        """Process a game without player comment - store replay data for later human analysis"""
        try:
            self.logger.info(f"Processing game without comment for {game_data.get('opponent_name', 'Unknown')} - storing for later human analysis")
            
            # Extract build order data if available
            build_data = game_data.get('build_order', [])
            
            if build_data:
                # Store replay data for later human analysis - NO AI commentary
                replay_data = {
                    'build_data': build_data,
                    'game_data': game_data,
                    'timestamp': datetime.now().isoformat(),
                    'needs_human_analysis': True,
                    'has_player_comment': False
                }
                
                # Store in a separate queue for human review
                if not hasattr(self, 'pending_human_analysis'):
                    self.pending_human_analysis = []
                
                self.pending_human_analysis.append(replay_data)
                
                self.logger.info(f"Stored replay data for {game_data.get('opponent_name', 'Unknown')} - awaiting human analysis")
                
        except Exception as e:
            self.logger.error(f"Error processing game without comment: {e}")
    
    def _guess_strategy_from_build(self, build_data):
        """AI attempts to identify strategy from build order - first 60 supply focus"""
        try:
            if not build_data:
                return "Unknown strategy"
            
            # Only analyze first 60 supply (configurable threshold)
            early_build = [step['name'] for step in build_data if step.get('supply', 0) <= config.BUILD_ORDER_COUNT_TO_ANALYZE]
            
            # Very basic classification - system learns from your comments
            if len(early_build) >= 5:
                # Look for obvious early aggression indicators
                if 'SpawningPool' in early_build and 'Zergling' in early_build:
                    return "Early zerg aggression"
                elif 'Barracks' in early_build and 'Reaper' in early_build:
                    return "Early terran aggression"
                elif 'Gateway' in early_build and 'Zealot' in early_build:
                    return "Early protoss aggression"
                elif len([s for s in early_build if 'Hatchery' in s or 'CommandCenter' in s or 'Nexus' in s]) >= 2:
                    return "Economic expansion"
                else:
                    return "Standard early game"
            else:
                return "Insufficient early game data"
            
        except Exception as e:
            self.logger.error(f"Error guessing strategy: {e}")
            return "Unknown strategy"
    
    def _calculate_ai_confidence(self, build_data):
        """Calculate how confident the AI is in its strategy guess - first 60 supply focus"""
        try:
            if not build_data:
                return 0.0
            
            confidence = 0.0
            
            # Only analyze first 60 supply (configurable threshold)
            early_build = [step['name'] for step in build_data if step.get('supply', 0) <= config.BUILD_ORDER_COUNT_TO_ANALYZE]
            
            # More early game data = higher confidence
            if len(early_build) >= 10:
                confidence += 0.3
            elif len(early_build) >= 5:
                confidence += 0.2
            
            # Clear early game indicators (learned from your comments, not hardcoded)
            if len(early_build) >= 3:
                # Basic confidence for having early game data
                confidence += 0.2
                
                # Additional confidence for clear early game patterns
                if any('Pool' in name for name in early_build) or any('Barracks' in name for name in early_build) or any('Gateway' in name for name in early_build):
                    confidence += 0.2
                
                # Economic indicators
                if len([s for s in early_build if 'Hatchery' in s or 'CommandCenter' in s or 'Nexus' in s]) >= 2:
                    confidence += 0.1
            
            return min(confidence, 1.0)  # Cap at 100%
            
        except Exception as e:
            self.logger.error(f"Error calculating AI confidence: {e}")
            return 0.0
    
    def _extract_keywords(self, comment):
        """Extract SC2 strategy keywords from comment with improved cleaning and deduplication"""
        try:
            # Get existing keywords from the database to learn what terms are meaningful
            existing_keywords = self._get_existing_keywords_from_db()
            
            # Clean the comment and extract keywords
            cleaned_comment = self._clean_comment_text(comment)
            comment_lower = cleaned_comment.lower()
            
            # Extract keywords that appear in the comment and exist in our learned vocabulary
            found_keywords = []
            for keyword in existing_keywords:
                if keyword.lower() in comment_lower:
                    found_keywords.append(keyword)
            
            # If no existing keywords match, extract basic terms and let the system learn
            if not found_keywords:
                # Simple word extraction for new learning
                words = comment_lower.split()
                # Filter out common non-strategic words
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
                # IMPORTANT: Allow 2-character words for SC2 terms like "DT", "GG", "APM", etc.
                strategic_words = [word for word in words if word not in stop_words and len(word) >= 2]
                found_keywords = strategic_words[:5]  # Limit to 5 most relevant words
            
            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for keyword in found_keywords:
                if keyword.lower() not in seen:
                    seen.add(keyword.lower())
                    unique_keywords.append(keyword)
            
            return unique_keywords
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            # Fallback: return basic words from comment
            return comment.lower().split()[:3]
    
    def _clean_comment_text(self, comment):
        """Clean comment text by removing punctuation and normalizing"""
        try:
            # Remove punctuation but keep spaces
            import re
            # Remove punctuation except for spaces and hyphens (for unit names like "Dark-Templar")
            cleaned = re.sub(r'[^\w\s-]', ' ', comment)
            # Normalize multiple spaces to single space
            cleaned = re.sub(r'\s+', ' ', cleaned)
            # Strip leading/trailing spaces
            cleaned = cleaned.strip()
            return cleaned
        except Exception as e:
            self.logger.error(f"Error cleaning comment text: {e}")
            return comment
    
    def _get_existing_keywords_from_db(self):
        """Get existing keywords from replay_summary data to learn vocabulary"""
        try:
            # This would query your existing replay_summary data to see what terms are already meaningful
            # For now, return an empty list to let the system learn from scratch
            # TODO: Implement query to extract meaningful terms from existing replay_summary entries
            return []
        except Exception as e:
            self.logger.error(f"Error getting existing keywords from DB: {e}")
            return []
    
    def _create_pattern_for_comment(self, comment_data):
        """Create a single pattern entry for a comment and reference it by all keywords"""
        try:
            # Get build order data from game
            build_data = comment_data['game_data'].get('build_order', [])
            
            if build_data:
                # Create pattern signature
                pattern_signature = self._create_pattern_signature(build_data)
                
                # Create single pattern entry
                pattern_entry = {
                    'signature': pattern_signature,
                    'comment': comment_data['comment'],
                    'game_data': comment_data['game_data'],
                    'keywords': comment_data['keywords']  # Store all keywords for this pattern
                }
                
                # Store pattern in a special 'all_patterns' list (not by keyword)
                if not hasattr(self, 'all_patterns'):
                    self.all_patterns = []
                self.all_patterns.append(pattern_entry)
                
                # Reference this pattern by each keyword (just store the index)
                for keyword in comment_data['keywords']:
                    if keyword not in self.patterns:
                        self.patterns[keyword] = []
                    # Store reference to the pattern (index in all_patterns)
                    self.patterns[keyword].append(len(self.all_patterns) - 1)
                
                self.logger.info(f"Created pattern with {len(comment_data['keywords'])} keywords")
                
        except Exception as e:
            self.logger.error(f"Error creating pattern: {e}")
    
    def _create_pattern_signature(self, build_data):
        """Create a signature for build order pattern with consolidated units"""
        signature = {
            'early_game': [],      # First 60 supply (configurable)
            'key_timings': {},     # Critical building timings
            'opening_sequence': [] # First 5-10 buildings
        }
        
        try:
            # Only analyze first 60 supply (configurable threshold)
            early_game_steps = []
            for step in build_data:
                supply = step.get('supply', 0)
                if supply <= config.BUILD_ORDER_COUNT_TO_ANALYZE:
                    early_game_steps.append(step)
            
            # Consolidate consecutive identical units with counts and order
            if early_game_steps:
                consolidated_build = self._consolidate_build_order(early_game_steps)
                signature['early_game'] = consolidated_build
                
                # Extract opening sequence (first 10 consolidated steps)
                signature['opening_sequence'] = consolidated_build[:10] if consolidated_build else []
            
            # Track key timings for critical buildings
            for step in build_data:
                name = step.get('name', '')
                time = step.get('time', 0)
                
                if name in ['SpawningPool', 'Barracks', 'Gateway', 'Forge', 'Factory', 
                           'RoachWarren', 'BanelingNest', 'Spire', 'NydusNetwork',
                           'TwilightCouncil', 'RoboticsFacility', 'Stargate',
                           'FusionCore', 'Armory', 'Starport', 'NuclearFacility']:
                    signature['key_timings'][name] = time
                    
        except Exception as e:
            self.logger.error(f"Error creating pattern signature: {e}")
            
        return signature
    
    def _consolidate_build_order(self, build_data):
        """Consolidate consecutive identical units with counts and order information"""
        try:
            if not build_data:
                return []
            
            consolidated = []
            current_unit = None
            current_count = 0
            current_supply = 0
            current_time = 0
            order = 1
            
            for i, step in enumerate(build_data):
                if isinstance(step, dict) and 'name' in step:
                    unit_name = step['name']
                    
                    if unit_name == current_unit:
                        # Same unit, increment count and update final values
                        current_count += 1
                        current_supply = step.get('supply', current_supply)
                        current_time = step.get('time', current_time)
                    else:
                        # Different unit, save previous and start new
                        if current_unit is not None:
                            consolidated.append({
                                'unit': current_unit,
                                'count': current_count,
                                'order': order,
                                'supply': current_supply,
                                'time': current_time
                            })
                            order += 1
                        
                        # Start new unit
                        current_unit = unit_name
                        current_count = 1
                        current_supply = step.get('supply', 0)
                        current_time = step.get('time', 0)
            
            # Don't forget the last unit - but only if we haven't already processed it
            if current_unit is not None and current_count > 0:
                # Check if this unit was already added in the loop
                if not consolidated or consolidated[-1]['unit'] != current_unit:
                    consolidated.append({
                        'unit': current_unit,
                        'count': current_count,
                        'order': order,
                        'supply': current_supply,
                        'time': current_time
                    })
            
            return consolidated
            
        except Exception as e:
            self.logger.error(f"Error consolidating build order: {e}")
            return []
    
    def _save_comment_to_db(self, game_data, comment):
        """Save comment to database for persistence"""
        try:
            # Save comment to the REPLAYS.Player_Comments table
            if hasattr(self.db, 'update_player_comments_in_last_replay'):
                success = self.db.update_player_comments_in_last_replay(comment)
                if success:
                    self.logger.info(f"Comment saved to database: {comment[:100]}...")
                else:
                    self.logger.warning(f"Failed to save comment to database: {comment[:100]}...")
            else:
                self.logger.warning("Database method update_player_comments_in_last_replay not available")
                self.logger.info(f"Comment logged only: {comment[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error saving comment to DB: {e}")
    
    def get_pattern_analysis(self, build_data, opponent_race):
        """Analyze current build against learned patterns"""
        try:
            current_signature = self._create_pattern_signature(build_data)
            matches = []
            
            # Check against all known patterns
            for keyword, patterns in self.patterns.items():
                for pattern in patterns:
                    similarity = self._calculate_similarity(current_signature, pattern['signature'])
                    
                    if similarity > 0.7:  # 70% similarity threshold
                        matches.append({
                            'keyword': keyword,
                            'confidence': similarity,
                            'comment': pattern['comment'],
                            'sample_count': len(patterns),
                            'has_player_comment': pattern.get('has_player_comment', False),
                            'ai_confidence': pattern.get('ai_confidence', 0.0)
                        })
            
            # Sort by confidence
            matches.sort(key=lambda x: x['confidence'], reverse=True)
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error in pattern analysis: {e}")
            return []
    
    def get_opponent_insights(self, opponent_name, current_build_data, opponent_race):
        """Get insights about a specific opponent based on learned patterns"""
        try:
            insights = []
            
            # Look for patterns involving this opponent
            for keyword, patterns in self.patterns.items():
                opponent_patterns = []
                
                for pattern in patterns:
                    # Check if this pattern involves the opponent
                    if self._is_opponent_in_pattern(pattern, opponent_name):
                        opponent_patterns.append(pattern)
                
                if opponent_patterns:
                    # Analyze current build against opponent's known patterns
                    current_signature = self._create_pattern_signature(current_build_data)
                    
                    for pattern in opponent_patterns:
                        similarity = self._calculate_similarity(current_signature, pattern['signature'])
                        
                        if similarity > 0.6:  # Lower threshold for opponent-specific insights
                            insight = self._format_opponent_insight(
                                opponent_name, pattern, similarity, current_build_data
                            )
                            insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting opponent insights: {e}")
            return []
    
    def _is_opponent_in_pattern(self, pattern, opponent_name):
        """Check if a pattern involves a specific opponent"""
        try:
            game_data = pattern.get('game_data', {})
            return game_data.get('opponent_name') == opponent_name
        except:
            return False
    
    def _format_opponent_insight(self, opponent_name, pattern, similarity, current_build):
        """Format an opponent-specific insight"""
        try:
            if pattern.get('has_player_comment', False):
                # Expert insight from your comment
                return {
                    'type': 'expert_insight',
                    'message': f"Last time vs. {opponent_name}, you noted: '{pattern['comment']}'",
                    'confidence': similarity,
                    'source': 'player_comment'
                }
            else:
                # AI-generated insight
                ai_confidence = pattern.get('ai_confidence', 0.0)
                return {
                    'type': 'ai_insight',
                    'message': f"I think based on previous games vs. {opponent_name}, this looks like {pattern['comment'].replace('AI detected: ', '')}",
                    'confidence': similarity,
                    'ai_confidence': ai_confidence,
                    'source': 'ai_learning'
                }
                
        except Exception as e:
            self.logger.error(f"Error formatting opponent insight: {e}")
            return {
                'type': 'error',
                'message': f"Error analyzing {opponent_name}'s patterns",
                'confidence': 0.0
            }
    
    def _calculate_similarity(self, current, known):
        """Calculate similarity between two build signatures"""
        try:
            score = 0.0
            total_checks = 0
            
            # Early game similarity - handle both old and new formats
            if current['early_game'] and known['early_game']:
                current_units = self._extract_unit_names(current['early_game'])
                known_units = self._extract_unit_names(known['early_game'])
                
                early_match = len(set(current_units) & set(known_units))
                early_total = len(set(current_units) | set(known_units))
                if early_total > 0:
                    score += (early_match / early_total) * 0.4  # 40% weight
                    total_checks += 1
            
            # Building sequence similarity
            if current['opening_sequence'] and known['opening_sequence']:
                current_seq = self._extract_unit_names(current['opening_sequence'])
                known_seq = self._extract_unit_names(known['opening_sequence'])
                
                seq_match = len(set(current_seq) & set(known_seq))
                seq_total = len(set(current_seq) | set(known_seq))
                if seq_total > 0:
                    score += (seq_match / seq_total) * 0.3  # 30% weight
                    total_checks += 1
            
            # Timing similarity
            if current['key_timings'] and known['key_timings']:
                timing_matches = 0
                timing_total = 0
                for building in set(current['key_timings'].keys()) & set(known['key_timings'].keys()):
                    current_time = current['key_timings'][building]
                    known_time = known['key_timings'][building]
                    time_diff = abs(current_time - known_time)
                    if time_diff <= 30:  # Within 30 seconds
                        timing_matches += 1
                    timing_total += 1
                
                if timing_total > 0:
                    score += (timing_matches / timing_total) * 0.3  # 30% weight
                    total_checks += 1
            
            # Normalize score
            if total_checks > 0:
                return score / total_checks
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _extract_unit_names(self, early_game):
        """Extract unit names from early_game list, handling both old and new formats"""
        try:
            unit_names = []
            for entry in early_game:
                if isinstance(entry, dict) and 'unit' in entry:
                    # New consolidated format
                    unit_names.append(entry['unit'])
                elif isinstance(entry, str):
                    # Old format
                    unit_names.append(entry)
            return unit_names
        except Exception as e:
            self.logger.error(f"Error extracting unit names: {e}")
            return []
    
    def get_learning_stats(self):
        """Get statistics about the learning system"""
        stats = {
            'total_keywords': len(self.comment_keywords),
            'total_patterns': len(self.all_patterns) if hasattr(self, 'all_patterns') else 0,
            'keyword_breakdown': {k: len(v) for k, v in self.comment_keywords.items()},
            'pattern_breakdown': {k: len(v) for k, v in self.patterns.items()},
            'ai_learned_patterns': len([p for p in (self.all_patterns if hasattr(self, 'all_patterns') else []) if not p.get('has_player_comment', False)]),
            'expert_patterns': len([p for p in (self.all_patterns if hasattr(self, 'all_patterns') else []) if p.get('has_player_comment', False)])
        }
        return stats
    
    def get_game_start_insights(self, opponent_name, opponent_race):
        """Get insights when starting a new game against a known opponent"""
        try:
            insights = []
            
            # Look for opponent-specific patterns
            opponent_patterns = []
            for keyword, patterns in self.patterns.items():
                for pattern in patterns:
                    if self._is_opponent_in_pattern(pattern, opponent_name):
                        opponent_patterns.append(pattern)
            
            if opponent_patterns:
                # Group by strategy type
                strategy_groups = {}
                for pattern in opponent_patterns:
                    strategy = pattern['comment'].replace('AI detected: ', '')
                    if strategy not in strategy_groups:
                        strategy_groups[strategy] = []
                    strategy_groups[strategy].append(pattern)
                
                # Generate insights for each strategy
                for strategy, patterns in strategy_groups.items():
                    # Check if you have expert insight for this strategy
                    expert_patterns = [p for p in patterns if p.get('has_player_comment', False)]
                    ai_patterns = [p for p in patterns if not p.get('has_player_comment', False)]
                    
                    if expert_patterns:
                        # Use your expert insight
                        insight = {
                            'type': 'expert_insight',
                            'message': f"🎯 {opponent_name} tends to do {strategy} - you noted this before",
                            'confidence': 'high',
                            'source': 'player_comment',
                            'strategy': strategy
                        }
                    else:
                        # Use AI learning
                        avg_confidence = sum(p.get('ai_confidence', 0.0) for p in ai_patterns) / len(ai_patterns)
                        insight = {
                            'type': 'ai_insight',
                            'message': f"🤖 I think based on previous games vs. {opponent_name}, they tend to do {strategy}",
                            'confidence': f"{avg_confidence:.1%}",
                            'source': 'ai_learning',
                            'strategy': strategy
                        }
                    
                    insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting game start insights: {e}")
            return []
    
    # File persistence methods
    def save_patterns_to_file(self):
        """Save all patterns to JSON files for persistence"""
        try:
            self.logger.info("Starting pattern learning save process...")
            # Save patterns with efficient structure (no duplication)
            patterns_file = os.path.join(self.data_dir, 'patterns.json')
            
            # Create efficient patterns structure - ONE pattern per unique build order
            efficient_patterns = {}
            pattern_id = 0
            
            # Track unique patterns by their signature hash
            seen_signatures = {}
            
            # Process all patterns from the centralized list
            if hasattr(self, 'all_patterns') and self.all_patterns:
                self.logger.info(f"Processing {len(self.all_patterns)} patterns for saving...")
                for pattern in self.all_patterns:
                    # Create a hash of the signature to identify duplicates
                    signature_str = json.dumps(pattern['signature'], sort_keys=True)
                    
                    if signature_str not in seen_signatures:
                        # This is a new unique pattern
                        pattern_id += 1
                        pattern_name = f"pattern_{pattern_id:03d}"
                        
                        # Create efficient pattern entry
                        efficient_patterns[pattern_name] = {
                            "signature": pattern['signature'],
                            "comment_id": f"comment_{pattern_id:03d}",
                            "game_id": f"game_{pattern_id:03d}",
                            "keywords": pattern.get('keywords', []),  # All keywords that reference this pattern
                            "comment": pattern['comment'],
                            "sample_count": 1,
                            "last_seen": datetime.now().isoformat(),
                            "strategy_type": self._classify_strategy(pattern),
                            "race": self._detect_race(pattern),
                            "confidence": pattern.get('ai_confidence', 0.8),
                            "game_data": pattern.get('game_data', {}),  # Include game data for comment management
                            "has_player_comment": pattern.get('has_player_comment', False)
                        }
                        
                        # Mark this signature as seen
                        seen_signatures[signature_str] = pattern_name
                    else:
                        # This pattern already exists, just add the keyword to the existing pattern
                        existing_pattern_name = seen_signatures[signature_str]
                        if 'keywords' not in efficient_patterns[existing_pattern_name]:
                            efficient_patterns[existing_pattern_name]['keywords'] = []
                        efficient_patterns[existing_pattern_name]['keywords'].extend(pattern.get('keywords', []))
                        efficient_patterns[existing_pattern_name]['sample_count'] += 1
            else:
                self.logger.warning("No all_patterns found - creating empty patterns file")
            
            with open(patterns_file, 'w') as f:
                json.dump(efficient_patterns, f, indent=2, default=str)
            self.logger.info(f"Saved {len(efficient_patterns)} patterns to {patterns_file}")
            
            # Save comments with efficient structure (no duplication)
            comments_file = os.path.join(self.data_dir, 'comments.json')
            
            # Create efficient structure: comments array + keyword index
            comments_data = {
                "comments": [],
                "keyword_index": {}
            }
            
            # Add all unique comments
            comment_id = 0
            seen_comments = set()
            
            for keyword, comment_list in self.comment_keywords.items():
                for comment_data in comment_list:
                    # Create unique comment ID
                    comment_text = comment_data['comment']
                    if comment_text not in seen_comments:
                        comment_id += 1
                        comment_entry = {
                            "id": f"comment_{comment_id:03d}",
                            "raw_comment": comment_data.get('raw_comment', comment_text),
                            "cleaned_comment": comment_data.get('cleaned_comment', comment_text),
                            "comment": comment_text,  # Keep for backward compatibility
                            "keywords": comment_data['keywords'],
                            "game_data": comment_data['game_data'],
                            "timestamp": comment_data['timestamp'],
                            "has_player_comment": comment_data['has_player_comment']
                        }
                        comments_data["comments"].append(comment_entry)
                        seen_comments.add(comment_text)
                        
                        # Add to keyword index
                        for kw in comment_data['keywords']:
                            if kw not in comments_data["keyword_index"]:
                                comments_data["keyword_index"][kw] = []
                            comments_data["keyword_index"][kw].append(f"comment_{comment_id:03d}")
            
            with open(comments_file, 'w') as f:
                json.dump(comments_data, f, indent=2, default=str)
            self.logger.info(f"Saved {len(comments_data['comments'])} comments to {comments_file}")
            
            # Save learning stats
            stats_file = os.path.join(self.data_dir, 'learning_stats.json')
            stats = self.get_learning_stats()
            stats['last_saved'] = datetime.now().isoformat()
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            self.logger.info(f"Saved learning stats to {stats_file}")
            
            self.logger.info("Pattern learning save process completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving patterns to file: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _classify_strategy(self, pattern):
        """Classify the strategy type based on pattern data"""
        try:
            signature = pattern.get('signature', {})
            early_game = signature.get('early_game', [])
            
            # Handle new consolidated format
            for entry in early_game:
                if isinstance(entry, dict) and 'unit' in entry:
                    unit_name = entry['unit']
                    if 'Pool' in unit_name:
                        return "zerg_aggression"
                    elif 'Barracks' in unit_name:
                        return "terran_aggression"
                    elif 'Gateway' in unit_name:
                        return "protoss_aggression"
                    elif 'Hatchery' in unit_name or 'CommandCenter' in unit_name or 'Nexus' in unit_name:
                        # Count economic buildings
                        economic_count = sum(1 for e in early_game if isinstance(e, dict) and 'unit' in e and 
                                           any(eco in e['unit'] for eco in ['Hatchery', 'CommandCenter', 'Nexus']))
                        if economic_count >= 2:
                            return "economic_expansion"
            
            # Fallback to old format for backward compatibility
            for entry in early_game:
                if isinstance(entry, str):
                    if 'Pool' in entry:
                        return "zerg_aggression"
                    elif 'Barracks' in entry:
                        return "terran_aggression"
                    elif 'Gateway' in entry:
                        return "protoss_aggression"
                    elif 'Hatchery' in entry or 'CommandCenter' in entry or 'Nexus' in entry:
                        # Count economic buildings
                        economic_count = sum(1 for e in early_game if isinstance(e, str) and 
                                           any(eco in e for eco in ['Hatchery', 'CommandCenter', 'Nexus']))
                        if economic_count >= 2:
                            return "economic_expansion"
            
            return "standard_opening"
        except:
            return "unknown_strategy"
    
    def _detect_race(self, pattern):
        """Detect the race from pattern data"""
        try:
            signature = pattern.get('signature', {})
            early_game = signature.get('early_game', [])
            
            # Handle new consolidated format
            for entry in early_game:
                if isinstance(entry, dict) and 'unit' in entry:
                    unit_name = entry['unit']
                    if 'Pool' in unit_name:
                        return "zerg"
                    elif 'Barracks' in unit_name:
                        return "terran"
                    elif 'Gateway' in unit_name:
                        return "protoss"
            
            # Fallback to old format for backward compatibility
            for entry in early_game:
                if isinstance(entry, str):
                    if 'Pool' in entry:
                        return "zerg"
                    elif 'Barracks' in entry:
                        return "terran"
                    elif 'Gateway' in entry:
                        return "protoss"
            
            return "unknown"
        except:
            return "unknown"
    
    def load_patterns_from_file(self):
        """Load patterns from JSON files on startup"""
        try:
            # Load patterns
            patterns_file = os.path.join(self.data_dir, 'patterns.json')
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                    
                    # Reconstruct all_patterns from saved data
                    self.all_patterns = []
                    for pattern_name, pattern_data in patterns_data.items():
                        # Convert saved pattern back to all_patterns format
                        pattern_entry = {
                            'signature': pattern_data.get('signature', {}),
                            'comment': pattern_data.get('comment', ''),
                            'keywords': pattern_data.get('keywords', []),
                            'game_data': pattern_data.get('game_data', {}),
                            'has_player_comment': pattern_data.get('has_player_comment', False),
                            'ai_confidence': pattern_data.get('confidence', 0.8),
                            'timestamp': pattern_data.get('last_seen', datetime.now().isoformat())
                        }
                        self.all_patterns.append(pattern_entry)
                        
                        # Also reconstruct patterns by keyword for backward compatibility
                        for keyword in pattern_data.get('keywords', []):
                            if keyword not in self.patterns:
                                self.patterns[keyword] = []
                            self.patterns[keyword].append(pattern_entry)
                
                self.logger.info(f"Loaded {len(patterns_data)} pattern categories from file")
            
            # Load comments with efficient structure
            comments_file = os.path.join(self.data_dir, 'comments.json')
            if os.path.exists(comments_file):
                with open(comments_file, 'r') as f:
                    comments_data = json.load(f)
                    
                    # Reconstruct comment_keywords from efficient structure
                    for comment in comments_data.get('comments', []):
                        comment_id = comment['id']
                        keywords = comment.get('keywords', [])
                        
                        # Add to each keyword's list
                        for keyword in keywords:
                            if keyword not in self.comment_keywords:
                                self.comment_keywords[keyword] = []
                            
                            # Create the comment data structure
                            comment_entry = {
                                'raw_comment': comment.get('raw_comment', comment['comment']),
                                'cleaned_comment': comment.get('cleaned_comment', comment['comment']),
                                'comment': comment['comment'],  # Keep for backward compatibility
                                'keywords': comment['keywords'],
                                'game_data': comment['game_data'],
                                'timestamp': comment['timestamp'],
                                'has_player_comment': comment.get('has_player_comment', True)
                            }
                            self.comment_keywords[keyword].append(comment_entry)
                
                self.logger.info(f"Loaded {len(comments_data.get('comments', []))} comments from file")
                
        except Exception as e:
            self.logger.error(f"Error loading patterns from file: {e}")
            # Continue with empty patterns if loading fails
    
    def get_total_patterns(self):
        """Get total number of patterns stored"""
        return sum(len(patterns) for patterns in self.patterns.values())
    
    def get_new_game_insights(self, opponent_name, opponent_race):
        """Get insights for NEW games against previous opponents (no existing player_comments)"""
        try:
            insights = []
            
            # Look for patterns involving this opponent that DON'T have player comments
            opponent_ai_patterns = []
            for keyword, patterns in self.patterns.items():
                for pattern in patterns:
                    if (self._is_opponent_in_pattern(pattern, opponent_name) and 
                        not pattern.get('has_player_comment', False)):
                        opponent_ai_patterns.append(pattern)
            
            if opponent_ai_patterns:
                # Group by strategy type
                strategy_groups = {}
                for pattern in opponent_ai_patterns:
                    strategy = pattern['comment'].replace('AI detected: ', '')
                    if strategy not in strategy_groups:
                        strategy_groups[strategy] = []
                    strategy_groups[strategy].append(pattern)
                
                # Generate AI insights for each strategy
                for strategy, patterns in strategy_groups.items():
                    avg_confidence = sum(p.get('ai_confidence', 0.0) for p in patterns) / len(patterns)
                    
                    insight = {
                        'type': 'ai_insight',
                        'message': f"🤖 I think based on previous games vs. {opponent_name}, they tend to do {strategy}",
                        'confidence': f"{avg_confidence:.1%}",
                        'source': 'ai_learning',
                        'strategy': strategy
                    }
                    
                    insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting new game insights: {e}")
            return []
    
    def _get_input_with_timeout(self, prompt, timeout_seconds):
        """Get user input with a timeout. Returns None if timeout or no input."""
        import sys
        import select
        import threading

        
        # For Windows compatibility, use threading approach
        if sys.platform.startswith('win'):
            result = [None]
            
            def get_input():
                try:
                    # Display prompt immediately and flush
                    print(prompt, end='', flush=True)
                    result[0] = input()
                except (EOFError, KeyboardInterrupt):
                    result[0] = None
            
            input_thread = threading.Thread(target=get_input, daemon=True)
            input_thread.start()
            input_thread.join(timeout_seconds)
            
            if input_thread.is_alive():
                self.logger.info(f"Input timeout after {timeout_seconds} seconds")
                return None
            
            return result[0]
        else:
            # Unix/Linux approach with select
            print(prompt, end='', flush=True)
            ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
            
            if ready:
                return sys.stdin.readline().rstrip('\n')
            else:
                self.logger.info(f"Input timeout after {timeout_seconds} seconds")
                return None

    def _generate_game_id(self, game_data):
        """Generate a unique identifier for a game to detect duplicates"""
        try:
            # Create a unique ID based on opponent, map, duration, and approximate time
            opponent = game_data.get('opponent_name', 'Unknown')
            map_name = game_data.get('map', 'Unknown')
            duration = game_data.get('duration', 'Unknown')
            
            # For date, use just the date part (not time) to handle replay viewing on different days
            date_str = game_data.get('date', '')
            if date_str:
                # Extract just the date part (YYYY-MM-DD)
                date_part = date_str.split(' ')[0] if ' ' in date_str else date_str
            else:
                date_part = 'Unknown'
            
            # Create a unique identifier
            game_id = f"{opponent}_{map_name}_{duration}_{date_part}"
            return game_id.lower().replace(' ', '_').replace(':', '_')
            
        except Exception as e:
            self.logger.error(f"Error generating game ID: {e}")
            return "unknown_game"
    
    def _is_game_already_processed(self, game_id):
        """Check if a game has already been processed (prevents duplicate learning from replays)"""
        try:
            # Check if we have any patterns or comments for this game ID
            # This prevents the system from prompting again when watching the same replay
            
            # Look through existing patterns for this game
            for pattern_list in self.patterns.values():
                for pattern in pattern_list:
                    if isinstance(pattern, dict) and 'game_data' in pattern and pattern['game_data']:
                        pattern_game_id = self._generate_game_id(pattern['game_data'])
                        if pattern_game_id == game_id:
                            return True
            
            # Look through existing comments for this game
            for comment_list in self.comment_keywords.values():
                for comment_data in comment_list:
                    if isinstance(comment_data, dict) and 'game_data' in comment_data and comment_data['game_data']:
                        comment_game_id = self._generate_game_id(comment_data['game_data'])
                        if comment_game_id == game_id:
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if game already processed: {e}")
            return False
    
    def _find_game_by_details(self, opponent_name, map_name, date):
        """Find a game by opponent, map, and approximate date"""
        try:
            # Look through all patterns to find matching game
            if hasattr(self, 'all_patterns'):
                for pattern in self.all_patterns:
                    game_data = pattern.get('game_data', {})
                    if (game_data.get('opponent_name', '').lower() == opponent_name.lower() and
                        game_data.get('map', '').lower() == map_name.lower()):
                        
                        # Check if date is close (within 1 day)
                        game_date = game_data.get('date', '')
                        if game_date:
                            try:
                                from datetime import datetime
                                game_dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                                search_dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                                date_diff = abs((game_dt - search_dt).days)
                                
                                if date_diff <= 1:  # Within 1 day
                                    return game_data
                            except:
                                # If date parsing fails, just check if dates are similar strings
                                if date in game_date or game_date in date:
                                    return game_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding game by details: {e}")
            return None
    
    def _upgrade_ai_pattern_to_player_comment(self, game_data, comment):
        """Upgrade an AI-generated pattern to include player comment"""
        try:
            game_id = self._generate_game_id(game_data)
            
            # Find and update the AI pattern
            if hasattr(self, 'all_patterns'):
                for pattern in self.all_patterns:
                    if (pattern.get('game_data') and 
                        self._generate_game_id(pattern['game_data']) == game_id):
                        
                        # Update the pattern to include player comment
                        pattern['has_player_comment'] = True
                        pattern['comment'] = comment
                        pattern['raw_comment'] = comment
                        pattern['cleaned_comment'] = self._clean_comment_text(comment)
                        
                        # Extract new keywords from the comment
                        new_keywords = self._extract_keywords(comment)
                        pattern['keywords'] = new_keywords
                        
                        self.logger.info(f"Upgraded AI pattern to player comment: {comment}")
                        break
                        
        except Exception as e:
            self.logger.error(f"Error upgrading AI pattern: {e}")
    
    def _replace_ai_pattern_with_player_comment(self, game_data, comment):
        """Replace an AI-generated pattern with a player comment"""
        try:
            game_id = self._generate_game_id(game_data)
            
            # Find and remove the old AI pattern
            if hasattr(self, 'all_patterns'):
                for i, pattern in enumerate(self.all_patterns):
                    if (pattern.get('game_data') and 
                        self._generate_game_id(pattern['game_data']) == game_id):
                        
                        # Remove the old pattern
                        old_pattern = self.all_patterns.pop(i)
                        
                        # Also remove from patterns by keyword
                        old_keyword = old_pattern.get('comment', '').replace('AI detected: ', '').lower().replace(' ', '_')
                        if old_keyword in self.patterns:
                            self.patterns[old_keyword] = [p for p in self.patterns[old_keyword] 
                                                        if p.get('game_data') != game_data]
                        
                        self.logger.info(f"Replaced AI pattern with player comment: {comment}")
                        break
                        
        except Exception as e:
            self.logger.error(f"Error replacing AI pattern: {e}")
