#!/usr/bin/env python3

import json
import re
import os
from datetime import datetime
from collections import defaultdict
import logging

from settings import config

class SC2PatternLearner:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.patterns = defaultdict(list)
        self.comment_keywords = defaultdict(list)
        
        # Ensure data directory exists
        os.makedirs(config.PATTERN_DATA_DIR, exist_ok=True)
        
        # Load existing patterns from file
        self.load_patterns_from_file()
        self.logger.info(f"Pattern learning system initialized with {self.get_total_patterns()} patterns")
        
    def prompt_for_player_comment(self, game_data):
        """
        Gracefully prompt for player comment after game ends
        Shows game details and handles input without blocking
        """
        try:
            # Check if we've already processed this game (prevents duplicate prompts when watching replays)
            game_id = self._generate_game_id(game_data)
            if self._is_game_already_processed(game_id):
                self.logger.info(f"Game already processed (ID: {game_id}), skipping comment prompt")
                print(f"⏭️  Game already processed ({game_data.get('opponent_name', 'Unknown')} on {game_data.get('map', 'Unknown')}) - skipping comment prompt")
                return None
            
            # Format game summary for the prompt
            game_summary = self._format_game_summary(game_data)
            
            print("\n" + "="*60)
            print("🎮 GAME COMPLETED - ENTER PLAYER COMMENT")
            print("="*60)
            print(game_summary)
            print("="*60)
            
            # Non-blocking input with clear instructions
            comment = input("Enter player comment about the game (or press Enter to skip): ").strip()
            
            if comment:
                print(f"✅ Comment saved: {comment}")
                self._process_new_comment(game_data, comment)
                return comment
            else:
                print("⏭️  Skipping comment input")
                return None
                
        except (EOFError, KeyboardInterrupt):
            print("⏭️  Input interrupted, continuing...")
            return None
        except Exception as e:
            self.logger.error(f"Error in comment prompt: {e}")
            print("❌ Error in comment input, continuing...")
            return None
    
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
            
            # Store comment with game data for learning
            comment_data = {
                'comment': comment,
                'keywords': keywords,
                'game_data': game_data,
                'timestamp': datetime.now().isoformat(),
                'has_player_comment': True  # Mark as having expert insight
            }
            
            # Save to database FIRST (this should always happen)
            self._save_comment_to_db(game_data, comment)
            
            # Update keyword patterns and analyze for new patterns (only if keywords found)
            if keywords:
                for keyword in keywords:
                    self.comment_keywords[keyword].append(comment_data)
                    # Analyze for new patterns for each keyword
                    self._analyze_patterns(keyword, comment_data)
                
                # Save patterns to file for persistence
                self.save_patterns_to_file()
            
            self.logger.info(f"Processed new comment with keywords: {keywords}")
            
        except Exception as e:
            self.logger.error(f"Error processing comment: {e}")
    
    def process_game_without_comment(self, game_data):
        """Process a game without player comment - AI learns from replay data"""
        try:
            # Extract build order data if available
            build_data = game_data.get('build_order', [])
            
            if build_data:
                # Create pattern signature
                pattern_signature = self._create_pattern_signature(build_data)
                
                # Try to identify strategy based on learned patterns
                strategy_guess = self._guess_strategy_from_build(build_data)
                
                # Store as AI-learned pattern
                ai_comment_data = {
                    'comment': f"AI detected: {strategy_guess}",
                    'keywords': [strategy_guess.lower().replace(' ', '_')],
                    'game_data': game_data,
                    'timestamp': datetime.now().isoformat(),
                    'has_player_comment': False,  # Mark as AI-generated
                    'ai_confidence': self._calculate_ai_confidence(build_data)
                }
                
                # Store in patterns
                keyword = strategy_guess.lower().replace(' ', '_')
                self.patterns[keyword].append(ai_comment_data)
                
                # Auto-save patterns to file
                self.save_patterns_to_file()
                
                self.logger.info(f"AI learned pattern: {strategy_guess} (confidence: {ai_comment_data['ai_confidence']:.1%})")
                
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
        """Extract SC2 strategy keywords from comment by learning from existing replay_summary data"""
        try:
            # Get existing keywords from the database to learn what terms are meaningful
            existing_keywords = self._get_existing_keywords_from_db()
            
            # Extract keywords that appear in the comment and exist in our learned vocabulary
            found_keywords = []
            comment_lower = comment.lower()
            
            for keyword in existing_keywords:
                if keyword.lower() in comment_lower:
                    found_keywords.append(keyword)
            
            # If no existing keywords match, extract basic terms and let the system learn
            if not found_keywords:
                # Simple word extraction for new learning
                words = comment_lower.split()
                # Filter out common non-strategic words
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
                strategic_words = [word for word in words if word not in stop_words and len(word) > 2]
                found_keywords = strategic_words[:5]  # Limit to 5 most relevant words
            
            return found_keywords
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            # Fallback: return basic words from comment
            return comment.lower().split()[:3]
    
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
    
    def _analyze_patterns(self, keyword, comment_data):
        """Analyze build patterns for a specific keyword"""
        try:
            # Get build order data from game
            build_data = comment_data['game_data'].get('build_order', [])
            
            if build_data:
                # Create pattern signature
                pattern_signature = self._create_pattern_signature(build_data)
                
                # Store pattern
                self.patterns[keyword].append({
                    'signature': pattern_signature,
                    'comment': comment_data['comment'],
                    'game_data': comment_data['game_data']
                })
                
                self.logger.info(f"Added pattern for keyword '{keyword}': {len(self.patterns[keyword])} samples")
                
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
    
    def _create_pattern_signature(self, build_data):
        """Create a signature for build order pattern - first 60 supply focus"""
        signature = {
            'early_game': [],      # First 60 supply (configurable)
            'key_timings': {},     # Critical building timings
            'opening_sequence': [] # First 5-10 buildings
        }
        
        try:
            early_game_steps = []
            
            for step in build_data:
                supply = step.get('supply', 0)
                name = step.get('name', '')
                time = step.get('time', 0)
                
                # Only analyze first 60 supply (configurable threshold)
                if supply <= config.BUILD_ORDER_COUNT_TO_ANALYZE:
                    early_game_steps.append(step)
                    signature['early_game'].append(name)
                    
                    # Track key timings for critical buildings
                    if name in ['SpawningPool', 'Barracks', 'Gateway', 'Forge', 'Factory', 
                               'RoachWarren', 'BanelingNest', 'Spire', 'NydusNetwork',
                               'TwilightCouncil', 'RoboticsFacility', 'Stargate',
                               'FusionCore', 'Armory', 'Starport', 'NuclearFacility']:
                        signature['key_timings'][name] = time
                    
                    # Track opening sequence (first 10 buildings)
                    if len(signature['opening_sequence']) < 10:
                        signature['opening_sequence'].append(name)
                    
        except Exception as e:
            self.logger.error(f"Error creating pattern signature: {e}")
            
        return signature
    
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
            
            # Early game similarity
            if current['early_game'] and known['early_game']:
                early_match = len(set(current['early_game']) & set(known['early_game']))
                early_total = len(set(current['early_game']) | set(known['early_game']))
                if early_total > 0:
                    score += (early_match / early_total) * 0.4  # 40% weight
                    total_checks += 1
            
            # Building sequence similarity
            if current['opening_sequence'] and known['opening_sequence']:
                seq_match = len(set(current['opening_sequence']) & set(known['opening_sequence']))
                seq_total = len(set(current['opening_sequence']) | set(known['opening_sequence']))
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
    
    def get_learning_stats(self):
        """Get statistics about the learning system"""
        stats = {
            'total_keywords': len(self.comment_keywords),
            'total_patterns': sum(len(patterns) for patterns in self.patterns.values()),
            'keyword_breakdown': {k: len(v) for k, v in self.comment_keywords.items()},
            'pattern_breakdown': {k: len(v) for k, v in self.patterns.items()},
            'ai_learned_patterns': len([p for patterns in self.patterns.values() for p in patterns if not p.get('has_player_comment', False)]),
            'expert_patterns': len([p for patterns in self.patterns.values() for p in patterns if p.get('has_player_comment', False)])
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
            # Save patterns with efficient structure (no duplication)
            patterns_file = os.path.join(config.PATTERN_DATA_DIR, 'patterns.json')
            
            # Create efficient patterns structure
            efficient_patterns = {}
            pattern_id = 0
            
            # Process each pattern category
            for keyword, pattern_list in self.patterns.items():
                for pattern in pattern_list:
                    pattern_id += 1
                    pattern_name = f"{keyword}_{pattern_id:03d}"
                    
                    # Create efficient pattern signature
                    efficient_patterns[pattern_name] = {
                        "signature": pattern.get('signature', {}),
                        "comment_id": f"comment_{pattern_id:03d}",
                        "game_id": f"game_{pattern_id:03d}",
                        "sample_count": 1,
                        "last_seen": datetime.now().isoformat(),
                        "strategy_type": self._classify_strategy(pattern),
                        "race": self._detect_race(pattern),
                        "confidence": pattern.get('ai_confidence', 0.8)
                    }
            
            with open(patterns_file, 'w') as f:
                json.dump(efficient_patterns, f, indent=2, default=str)
            
            # Save comments with efficient structure (no duplication)
            comments_file = os.path.join(config.PATTERN_DATA_DIR, 'comments.json')
            
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
                            "comment": comment_text,
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
            
            # Save learning stats
            stats_file = os.path.join(config.PATTERN_DATA_DIR, 'learning_stats.json')
            stats = self.get_learning_stats()
            stats['last_saved'] = datetime.now().isoformat()
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            self.logger.info(f"Patterns saved to {config.PATTERN_DATA_DIR}/")
            
        except Exception as e:
            self.logger.error(f"Error saving patterns to file: {e}")
    
    def _classify_strategy(self, pattern):
        """Classify the strategy type based on pattern data"""
        try:
            signature = pattern.get('signature', {})
            early_game = signature.get('early_game', [])
            
            # Basic strategy classification
            if any('Pool' in name for name in early_game):
                return "zerg_aggression"
            elif any('Barracks' in name for name in early_game):
                return "terran_aggression"
            elif any('Gateway' in name for name in early_game):
                return "protoss_aggression"
            elif len([s for s in early_game if 'Hatchery' in s or 'CommandCenter' in s or 'Nexus' in s]) >= 2:
                return "economic_expansion"
            else:
                return "standard_opening"
        except:
            return "unknown_strategy"
    
    def _detect_race(self, pattern):
        """Detect the race from pattern data"""
        try:
            signature = pattern.get('signature', {})
            early_game = signature.get('early_game', [])
            
            if any('Pool' in name for name in early_game):
                return "zerg"
            elif any('Barracks' in name for name in early_game):
                return "terran"
            elif any('Gateway' in name for name in early_game):
                return "protoss"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def load_patterns_from_file(self):
        """Load patterns from JSON files on startup"""
        try:
            # Load patterns
            patterns_file = os.path.join(config.PATTERN_DATA_DIR, 'patterns.json')
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                    # Convert back to defaultdict
                    for keyword, patterns in patterns_data.items():
                        self.patterns[keyword] = patterns
                
                self.logger.info(f"Loaded {len(patterns_data)} pattern categories from file")
            
            # Load comments with efficient structure
            comments_file = os.path.join(config.PATTERN_DATA_DIR, 'comments.json')
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
                                'comment': comment['comment'],
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
