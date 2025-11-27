#!/usr/bin/env python3
"""
ML Opponent Analyzer - Enhanced version with priority system for player comments
"""

import json
import os
import re
from collections import Counter
from api.chat_utils import processMessageForOpenAI
import settings.config as config


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
    
    def match_build_against_all_patterns(self, build_order, opponent_race, logger, current_comment=None):
        """
        Match a build order against ALL learned patterns, regardless of opponent.
        Used for pattern validation display to show matches from similar strategies.
        
        Args:
            build_order: List of build order steps [{supply, name, time}, ...]
            opponent_race: Race of the opponent ('Terran', 'Protoss', 'Zerg')
            logger: Logger instance
            current_comment: Optional player comment for this game (for comment-based priority boosting)
            
        Returns:
            List of matched patterns sorted by similarity, or empty list
        """
        try:
            # Load learned patterns from COMMENTS (real game data)
            comments_data = self.load_learning_data()
            
            if not comments_data or not build_order:
                if logger:
                    logger.debug("No comments data or build order available for matching")
                return []
            
            # Extract comments with build order data
            comments_with_builds = [c for c in comments_data.get('comments', []) 
                                    if c.get('game_data', {}).get('build_order')]
            
            if not comments_with_builds:
                if logger:
                    logger.debug(f"No comments with build order data found (total comments: {len(comments_data.get('comments', []))})")
                return []
            
            if logger:
                logger.debug(f"Matching against {len(comments_with_builds)} comments with build data")
            
            # Set current comment for priority boosting (if provided)
            self._current_opponent_comment = current_comment if current_comment else ''
            
            # Convert comments to patterns format for matching
            # Each comment with build order becomes a pattern entry
            patterns_from_comments = []
            for comment in comments_with_builds:
                game_data = comment.get('game_data', {})
                build_data = game_data.get('build_order', [])
                comment_race = game_data.get('opponent_race', 'unknown')
                
                # Convert build_data format from {name, time, supply} to {unit, time, supply}
                # The signature extraction expects 'unit' field, not 'name'
                early_game_signature = []
                for i, step in enumerate(build_data):
                    early_game_signature.append({
                        'unit': step.get('name', ''),  # Convert 'name' to 'unit'
                        'time': step.get('time', 0),
                        'supply': step.get('supply', 0),
                        'count': 1,
                        'order': i + 1
                    })
                
                # Create pattern entry from comment
                pattern_entry = {
                    'signature': {
                        'early_game': early_game_signature
                    },
                    'comment': comment.get('comment', ''),
                    'game_data': game_data,
                    'race': comment_race.lower() if comment_race else 'unknown',
                    'has_player_comment': True,
                    'opponent_name': game_data.get('opponent_name', 'Unknown')
                }
                patterns_from_comments.append(pattern_entry)
            
            # Create patterns_data structure
            patterns_data_from_comments = {'patterns': patterns_from_comments}
            
            # Match build against comment-based patterns
            matched_patterns = self._match_build_against_patterns(build_order, patterns_data_from_comments, opponent_race, logger)
            
            # Clear current comment
            self._current_opponent_comment = ''
            
            # Add game context to each match for display
            for match in matched_patterns:
                # Try to find the original game this pattern came from
                match['game_info'] = {
                    'opponent_name': match.get('opponent_name', 'Unknown'),
                    'map': match.get('map', 'Unknown'),
                    'date': match.get('date', 'Unknown')
                }
            
            return matched_patterns
            
        except Exception as e:
            if logger:
                logger.error(f"Error matching build against all patterns: {e}")
            return []
    
    def analyze_opponent_for_chat(self, opponent_name, opponent_race, logger, db=None):
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
            # Get opponent's replay data from database (filtered by race)
            opponent_replay = db.check_player_and_race_exists(opponent_name, opponent_race)
            
            if not opponent_replay:
                if logger:
                    logger.debug(f"ML Analysis: No database records for opponent '{opponent_name}' as {opponent_race}")
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
        """
        NEW: Match opponent's build order against learned patterns using BUILD-TO-BUILD comparison.
        Player comments are labels only - matching is purely based on build signatures.
        Strategic items from SC2_STRATEGIC_ITEMS are weighted higher.
        """
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
            
            # Extract strategic items from new build (ignore workers/supply)
            new_build_strategic_items = self._extract_strategic_items_from_build(build_order, opponent_race)
            
            if not new_build_strategic_items:
                if logger:
                    logger.debug("No strategic items found in new build - cannot match")
                return []
            
            # Match against each pattern's build signature
            for pattern in patterns:
                # Skip patterns without signatures
                if 'signature' not in pattern:
                    continue
                
                # Skip generic test patterns
                comment = pattern.get('comment', '').lower()
                generic_indicators = ['hello world', 'first comment', 'test', 'computer']
                if any(indicator in comment for indicator in generic_indicators):
                    continue
                
                # Get pattern race - prefer explicit race field, fallback to signature detection
                pattern_signature = pattern.get('signature', {})
                pattern_race = pattern.get('race', '').lower()  # Use explicit race field first
                if not pattern_race or pattern_race == 'unknown':
                    pattern_race = self._determine_pattern_race_from_signature(pattern_signature)
                
                # Filter by race - strict filtering, skip if race doesn't match
                opponent_race_lower = opponent_race.lower() if opponent_race else 'unknown'
                if pattern_race and pattern_race != 'unknown' and pattern_race != opponent_race_lower:
                    if logger:
                        logger.debug(f"Pattern '{comment}' filtered by race: {pattern_race} != {opponent_race_lower}")
                    continue
                
                # Extract strategic items from pattern signature
                pattern_strategic_items = self._extract_strategic_items_from_signature(pattern_signature, opponent_race)
                
                if not pattern_strategic_items:
                    continue
                
                # Compare builds directly (build-to-build comparison)
                similarity_score = self._compare_build_signatures(
                    new_build_strategic_items,
                    pattern_strategic_items,
                    opponent_race,
                    logger
                )
                
                # Configurable minimum threshold
                min_threshold = getattr(config, 'ML_ANALYSIS_SIMILARITY_THRESHOLD', 0.05)
                if similarity_score > min_threshold:
                    matched_patterns.append({
                        'comment': pattern.get('comment', 'Unknown strategy'),
                        'keywords': pattern.get('keywords', [])[:10],  # For display only (labels)
                        'similarity': similarity_score,
                        'strategy_type': pattern.get('strategy_type', 'unknown'),
                        'race': pattern_race
                    })
            
            # Sort by similarity (highest first)
            matched_patterns.sort(key=lambda x: x['similarity'], reverse=True)
            
            if logger:
                logger.debug(f"Matched {len(matched_patterns)} patterns for opponent race {opponent_race}")
                for i, pattern in enumerate(matched_patterns[:10]):  # Show top 10 for debugging
                    logger.debug(f"  {i+1}. '{pattern['comment']}' - Score: {pattern['similarity']:.2f} (Race: {pattern.get('race', 'unknown')})")
                if len(matched_patterns) > 0:
                    best = matched_patterns[0]
                    logger.info(f"Best match: '{best['comment']}' at {best['similarity']:.2f} similarity")
            
            return matched_patterns
            
        except Exception as e:
            if logger:
                logger.error(f"Error matching build against patterns: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
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
                summary_parts.append(f"Build: {' -> '.join(strategic_elements[:3])}")
            
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

    def _extract_strategic_items_from_build(self, build_order, opponent_race):
        """
        Extract only strategic items from build order, filtering out workers and supply.
        Returns list of dicts with {name, timing, position} for weighting.
        """
        # Define workers and supply structures (to filter out)
        non_strategic = {
            'probe', 'scv', 'drone', 'mule',
            'pylon', 'supplydepot', 'overlord', 'overseer',
            'nexus', 'commandcenter', 'hatchery', 'lair', 'hive',
            'orbitalcommand', 'planetaryfortress'
        }
        
        # Get strategic items from config
        strategic_items = set()
        if opponent_race in config.SC2_STRATEGIC_ITEMS:
            race_items = config.SC2_STRATEGIC_ITEMS[opponent_race]
            for category in ['buildings', 'units', 'upgrades']:
                if category in race_items:
                    items = [item.strip().lower() for item in race_items[category].split(',')]
                    strategic_items.update(items)
        
        # Extract strategic items with timing info
        strategic_build_items = []
        for i, step in enumerate(build_order):
            name = step.get('name', '').lower()
            timing = step.get('time', 0)
            
            # Skip workers and supply
            if name in non_strategic:
                continue
            
            # Check if it's a strategic item
            if name in strategic_items:
                strategic_build_items.append({
                    'name': name,
                    'timing': timing,
                    'position': i,  # Position in build order (lower = earlier = more significant)
                    'supply': step.get('supply', 0)
                })
        
        return strategic_build_items
    
    def _determine_pattern_race_from_signature(self, signature):
        """Determine race from pattern signature by looking at units in build"""
        try:
            # Get all units from signature
            units = []
            if 'early_game' in signature:
                units.extend([item.get('unit', '').lower() for item in signature['early_game']])
            if 'opening_sequence' in signature:
                units.extend([item.get('unit', '').lower() for item in signature['opening_sequence']])
            if 'key_timings' in signature:
                units.extend([key.lower() for key in signature['key_timings'].keys()])
            
            # Check race-specific units
            zerg_units = {'drone', 'zergling', 'roach', 'hydralisk', 'mutalisk', 'baneling', 'hatchery', 'spawningpool', 'roachwarren'}
            terran_units = {'scv', 'marine', 'marauder', 'tank', 'hellion', 'barracks', 'factory', 'starport'}
            protoss_units = {'probe', 'zealot', 'stalker', 'adept', 'gateway', 'nexus', 'cyberneticscore'}
            
            for unit in units:
                if any(z in unit for z in zerg_units):
                    return 'zerg'
                if any(t in unit for t in terran_units):
                    return 'terran'
                if any(p in unit for p in protoss_units):
                    return 'protoss'
            
            return 'unknown'
        except:
            return 'unknown'
    
    def _extract_strategic_items_from_signature(self, signature, race):
        """Extract strategic items from a pattern signature"""
        try:
            strategic_items = []
            seen_items = {}  # Track items by name to avoid duplicates
            
            # Get strategic items from config
            strategic_item_names = set()
            if race in config.SC2_STRATEGIC_ITEMS:
                race_items = config.SC2_STRATEGIC_ITEMS[race]
                for category in ['buildings', 'units', 'upgrades']:
                    if category in race_items:
                        items = [item.strip().lower() for item in race_items[category].split(',')]
                        strategic_item_names.update(items)
            
            # Extract from key_timings (critical strategic buildings)
            if 'key_timings' in signature:
                for unit_name, raw_timing in signature['key_timings'].items():
                    unit_lower = unit_name.lower()
                    if unit_lower in strategic_item_names:
                        # Convert time string '1:28' to seconds (88)
                        if isinstance(raw_timing, str) and ':' in raw_timing:
                            try:
                                parts = raw_timing.split(':')
                                timing = int(parts[0]) * 60 + int(parts[1])
                            except:
                                timing = 0
                        else:
                            timing = raw_timing if isinstance(raw_timing, (int, float)) else 0
                        
                        seen_items[unit_lower] = {
                            'name': unit_lower,
                            'timing': timing,
                            'position': 0  # Key timings are most critical
                        }
            
            # Extract from early_game sequence (includes units AND buildings)
            # This is crucial for catching strategic units like Marine, Tank, etc.
            if 'early_game' in signature:
                for i, step in enumerate(signature['early_game']):
                    unit_name = step.get('unit', '').lower()
                    if unit_name in strategic_item_names:
                        # Convert time string '1:28' to seconds (88)
                        raw_time = step.get('time', 0)
                        if isinstance(raw_time, str) and ':' in raw_time:
                            try:
                                parts = raw_time.split(':')
                                timing = int(parts[0]) * 60 + int(parts[1])
                            except:
                                timing = 0
                        else:
                            timing = raw_time if isinstance(raw_time, (int, float)) else 0
                        
                        # Only add if not already seen, or if this is earlier
                        if unit_name not in seen_items:
                            seen_items[unit_name] = {
                                'name': unit_name,
                                'timing': timing,
                                'position': i
                            }
            
            # Convert to list
            strategic_items = list(seen_items.values())
            
            return strategic_items
        except Exception as e:
            return []
    
    def _compare_build_signatures(self, new_build_items, pattern_items, race, logger):
        """
        Compare two builds directly using strategic items with BIDIRECTIONAL matching.
        Returns similarity score 0-1 based on:
        - Which strategic items appear in both
        - Timing similarity for matching items
        - Strategic item weights from SC2_STRATEGIC_ITEMS
        - PENALTY for extra tech buildings in new build not in pattern
        """
        try:
            if not new_build_items or not pattern_items:
                return 0.0
            
            # Create lookup dictionaries by item name
            new_build_dict = {item['name']: item for item in new_build_items}
            pattern_dict = {item['name']: item for item in pattern_items}
            
            # Find matching items
            matching_items = set(new_build_dict.keys()) & set(pattern_dict.keys())
            
            if not matching_items:
                return 0.0
            
            # Define critical tech buildings that strongly differentiate strategies
            tech_buildings = {
                'banelingnest', 'roachwarren', 'spire', 'hydraliskden', 'lurkerden',
                'infestationpit', 'ultraliskcavern', 'nydusnetwork',
                'stargate', 'roboticsfacility', 'darkshrine', 'templararchive', 'fleetbeacon',
                'factory', 'starport', 'fusioncore', 'ghostacademy'
            }
            
            # Define expansion structures - CRITICAL for determining all-in vs macro strategies
            expansion_structures = {
                'commandcenter', 'nexus', 'hatchery'
            }
            
            # DIRECTION 1: Pattern → New Build (How well does new build match the pattern?)
            pattern_total_weight = 0.0
            pattern_matched_weight = 0.0
            
            for item_name, item_data in pattern_dict.items():
                timing = item_data['timing']
                # Defensive: Ensure timing is numeric
                try:
                    timing = float(timing) if not isinstance(timing, (int, float)) else timing
                except (ValueError, TypeError):
                    timing = 0
                
                # Extra weight for tech buildings
                is_tech = item_name in tech_buildings
                
                # Early timing bonus
                if timing < 300:  # 5 minutes
                    weight = 4.0 if is_tech else 3.0
                elif timing < 480:  # 8 minutes
                    weight = 3.0 if is_tech else 2.0
                else:
                    weight = 2.0 if is_tech else 1.0
                
                pattern_total_weight += weight
                
                # If this item exists in new build, add to matched weight
                if item_name in matching_items:
                    new_timing = new_build_dict[item_name]['timing']
                    # Defensive: Ensure timing is numeric
                    try:
                        new_timing = float(new_timing) if not isinstance(new_timing, (int, float)) else new_timing
                        timing = float(timing) if not isinstance(timing, (int, float)) else timing
                    except (ValueError, TypeError):
                        new_timing = 0
                        timing = 0
                    
                    # Timing similarity bonus (closer timing = higher score)
                    timing_diff = abs(new_timing - timing)
                    if timing_diff < 30:  # Within 30 seconds
                        timing_bonus = 1.0
                    elif timing_diff < 60:  # Within 1 minute
                        timing_bonus = 0.8
                    elif timing_diff < 120:  # Within 2 minutes
                        timing_bonus = 0.5
                    else:
                        timing_bonus = 0.3
                    
                    pattern_matched_weight += weight * timing_bonus
            
            # DIRECTION 2: New Build → Pattern (Penalty for extra strategic items in new build)
            new_total_weight = 0.0
            new_matched_weight = 0.0
            
            for item_name, item_data in new_build_dict.items():
                timing = item_data['timing']
                # Defensive: Ensure timing is numeric
                try:
                    timing = float(timing) if not isinstance(timing, (int, float)) else timing
                except (ValueError, TypeError):
                    timing = 0
                
                # Extra weight for tech buildings
                is_tech = item_name in tech_buildings
                
                # Early timing bonus
                if timing < 300:  # 5 minutes
                    weight = 4.0 if is_tech else 3.0
                elif timing < 480:  # 8 minutes
                    weight = 3.0 if is_tech else 2.0
                else:
                    weight = 2.0 if is_tech else 1.0
                
                new_total_weight += weight
                
                # If this item exists in pattern, add to matched weight
                if item_name in matching_items:
                    pattern_timing = pattern_dict[item_name]['timing']
                    # Defensive: Ensure timing is numeric
                    try:
                        pattern_timing = float(pattern_timing) if not isinstance(pattern_timing, (int, float)) else pattern_timing
                    except (ValueError, TypeError):
                        pattern_timing = 0
                    
                    # Timing similarity bonus
                    timing_diff = abs(timing - pattern_timing)
                    if timing_diff < 30:
                        timing_bonus = 1.0
                    elif timing_diff < 60:
                        timing_bonus = 0.8
                    elif timing_diff < 120:
                        timing_bonus = 0.5
                    else:
                        timing_bonus = 0.3
                    
                    new_matched_weight += weight * timing_bonus
            
            # Calculate bidirectional similarity
            pattern_similarity = pattern_matched_weight / pattern_total_weight if pattern_total_weight > 0 else 0.0
            new_similarity = new_matched_weight / new_total_weight if new_total_weight > 0 else 0.0
            
            # Use harmonic mean (penalizes mismatches more than arithmetic mean)
            # Combined with critical tech and expansion penalties, this provides balanced matching
            if pattern_similarity > 0 and new_similarity > 0:
                similarity = 2 * (pattern_similarity * new_similarity) / (pattern_similarity + new_similarity)
            else:
                similarity = 0.0
            
            # CRITICAL TECH MISMATCH PENALTY: If pattern has critical tech buildings that new build lacks, apply extra penalty
            # Critical tech buildings define the strategy (e.g., Forge = cannon rush, Stargate = air, Robo = robo bay)
            critical_tech = {
                # Protoss - tech that defines strategy
                'forge', 'stargate', 'roboticsfacility', 'darkshrine', 'templararchive', 'fleetbeacon',
                # Zerg - tech that defines strategy (roach/bane/spire are BIG differentiators)
                'roachwarren', 'banelingnest', 'spire', 'hydraliskden', 'infestationpit', 'ultraliskcavern', 'lurkerden',
                # Terran - tech that defines strategy
                'factory', 'starport', 'ghostacademy', 'fusioncore'
            }
            
            pattern_critical = set(item for item in pattern_dict.keys() if item in critical_tech)
            new_critical = set(item for item in new_build_dict.keys() if item in critical_tech)
            
            missing_critical = pattern_critical - new_critical  # Critical tech in pattern but not in new build
            
            if missing_critical and similarity > 0:
                # Calculate penalty based on ratio of matching critical tech
                # If pattern has 2 critical techs and new build has 1, penalty = 0.5
                # If pattern has 2 critical techs and new build has 0, penalty = 0.0
                matching_critical_count = len(pattern_critical & new_critical)
                total_critical_count = len(pattern_critical)
                
                if total_critical_count > 0:
                    critical_ratio = matching_critical_count / total_critical_count
                    # At least 50% match required to avoid heavy penalty
                    if critical_ratio < 0.5:
                        critical_penalty = critical_ratio * 0.4  # Scale 0-0.5 ratio to 0-0.2 penalty
                    else:
                        critical_penalty = 0.2 + (critical_ratio - 0.5) * 1.6  # Scale 0.5-1.0 to 0.2-1.0
                    
                    similarity *= critical_penalty
                    
                    if logger:
                        logger.debug(f"Critical tech: pattern has {pattern_critical}, new has {new_critical}. "
                                   f"Matching {matching_critical_count}/{total_critical_count}, penalty: {critical_penalty:.1%}")
            
            # EXPANSION PENALTY: Number of bases is CRITICAL - heavily penalize mismatches
            # Count expansion structures in each build (OrbitalCommand/PlanetaryFortress don't count - they're upgrades)
            # NOTE: Use original lists, not dicts, to count multiple expansions correctly
            pattern_expansions = sum(1 for item in pattern_items if item['name'] in expansion_structures)
            new_expansions = sum(1 for item in new_build_items if item['name'] in expansion_structures)
            
            # Apply expansion penalty based on difference
            expansion_diff = abs(pattern_expansions - new_expansions)
            if expansion_diff == 0:
                expansion_multiplier = 1.0  # Perfect match
            elif expansion_diff == 1:
                expansion_multiplier = 0.6  # 1 base difference = 40% penalty
            elif expansion_diff == 2:
                expansion_multiplier = 0.3  # 2 base difference = 70% penalty
            else:
                expansion_multiplier = 0.1  # 3+ base difference = 90% penalty (almost no match)
            
            # Apply the expansion penalty
            similarity *= expansion_multiplier
            
            if logger and expansion_diff > 0:
                logger.debug(f"Expansion mismatch: pattern={pattern_expansions} bases, new={new_expansions} bases, "
                           f"diff={expansion_diff}, penalty multiplier={expansion_multiplier:.1%}")
            
            return similarity
            
        except Exception as e:
            if logger:
                logger.error(f"Error comparing build signatures: {e}")
            return 0.0
    
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
            msg += "Keep it under 200 characters. Describe ONLY what the opponent does - their builds, strategies, and patterns. "
            msg += "CRITICAL: Be factual and analytical. Do NOT add mood, personality, or conversational elements. "
            msg += "Do NOT give advice, ask questions, request insights, or ask for recommendations. "
            msg += "Do NOT say things like 'should we play together' or any casual conversation. "
            msg += "Just state the analysis factually in a professional tone. "
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
                # Analysis based on pattern matching from similar opponents
                msg += "Pattern matched from similar opponents (not exact opponent history):\n"
                
                if data.get('matched_patterns'):
                    msg += "This opponent's build resembles strategies from other players:\n"
                    for pattern in data['matched_patterns'][:2]:
                        similarity = pattern['similarity'] * 100
                        msg += f"- {pattern['comment']} ({similarity:.0f}% match)\n"
                        if pattern.get('keywords'):
                            keywords = ", ".join(pattern['keywords'][:3])
                            msg += f"  Keywords: {keywords}\n"
                
                if data.get('build_order_preview'):
                    build_preview = [step['name'] for step in data['build_order_preview'][:5]]
                    msg += f"Their opening: {' -> '.join(build_preview)}\n"
            
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
            opponent_name, opponent_race, logger, db_instance
        )
        
        if analysis_data:
            # Generate and send ML analysis message
            analyzer.generate_ml_analysis_message(analysis_data, twitch_bot, logger, contextHistory)
            return True
        else:
            # No analysis data - send message indicating no strong matches
            from api.chat_utils import processMessageForOpenAI
            no_match_msg = ("Generate a concise message for Twitch chat. "
                           + "Say that there are no strong matches on the pattern analysis for this opponent. "
                           + "Keep it under 100 characters. "
                           + "Format: 'ML Analysis: [your message]' "
                           + "Be factual and analytical, not conversational. "
                           + f"Opponent: {opponent_name} ({opponent_race})\n\n"
                           + "Your message:")
            processMessageForOpenAI(twitch_bot, no_match_msg, "ml_analysis", logger, contextHistory)
            return True
            
    except Exception as e:
        if logger:
            logger.error(f"Error in game start ML analysis: {e}")
        return False
