#!/usr/bin/env python3
"""
SC2 Replay Strategic Analyzer

This script demonstrates how to analyze a replay using the learned patterns,
player comments, and strategic intelligence from the pattern learning system.
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime
import sys
import os

class SC2ReplayAnalyzer:
    def __init__(self):
        self.comments_data = self.load_comments_data()
        self.patterns_data = self.load_patterns_data()
        self.stats_data = self.load_stats_data()
        
    def load_comments_data(self):
        """Load the comments database"""
        try:
            with open('data/comments.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading comments data: {e}")
            return {"comments": [], "keyword_index": {}}
    
    def load_patterns_data(self):
        """Load the patterns database"""
        try:
            with open('data/patterns.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading patterns data: {e}")
            return {}
    
    def load_stats_data(self):
        """Load the learning statistics"""
        try:
            with open('data/learning_stats.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading stats data: {e}")
            return {"total_keywords": 0, "keyword_breakdown": {}}
    
    def analyze_opponent_intelligence(self, opponent_name):
        """Analyze historical data about a specific opponent"""
        # Find all games against this opponent
        opponent_games = [
            comment for comment in self.comments_data['comments']
            if comment['game_data']['opponent_name'] == opponent_name
        ]
        
        if not opponent_games:
            return {
                'known_opponent': False,
                'games_played': 0,
                'confidence': 0.0
            }
        
        # Calculate statistics
        total_games = len(opponent_games)
        wins = sum(1 for game in opponent_games if game['game_data']['result'] == 'Victory')
        win_rate = wins / total_games if total_games > 0 else 0
        
        # Extract strategic patterns
        all_keywords = []
        maps_played = []
        recent_strategies = []
        
        for game in opponent_games:
            all_keywords.extend(game['keywords'])
            maps_played.append(game['game_data']['map'])
            recent_strategies.append({
                'comment': game['comment'],
                'result': game['game_data']['result'],
                'map': game['game_data']['map'],
                'date': game['game_data']['date']
            })
        
        # Most common strategic themes
        keyword_frequency = Counter(all_keywords)
        common_strategies = keyword_frequency.most_common(5)
        
        # Preferred maps
        map_frequency = Counter(maps_played)
        
        # Calculate confidence based on sample size and recency
        confidence = min(1.0, (total_games * 0.2) + 0.3)  # Base confidence + sample boost
        
        return {
            'known_opponent': True,
            'games_played': total_games,
            'win_rate': win_rate,
            'confidence': confidence,
            'common_strategies': common_strategies,
            'preferred_maps': map_frequency.most_common(3),
            'recent_games': sorted(recent_strategies, 
                                 key=lambda x: x['date'], reverse=True)[:5],
            'strategic_advice': self.generate_strategic_advice(keyword_frequency, win_rate)
        }
    
    def analyze_build_order_patterns(self, build_order, player_race):
        """Analyze build order against learned patterns"""
        if not build_order:
            return {
                'pattern_matches': [],
                'confidence': 0.0,
                'strategic_classification': 'unknown'
            }
        
        # Extract key characteristics of the build
        build_signature = self.create_build_signature(build_order)
        
        # Find matching patterns
        pattern_matches = []
        for pattern_id, pattern_data in self.patterns_data.items():
            if 'signature' not in pattern_data:
                continue
                
            match_score = self.calculate_pattern_similarity(
                build_signature, pattern_data['signature']
            )
            
            if match_score > 0.3:  # Threshold for meaningful similarity
                pattern_matches.append({
                    'pattern_id': pattern_id,
                    'match_score': match_score,
                    'keywords': pattern_data.get('keywords', []),
                    'strategy_type': pattern_data.get('strategy_type', 'unknown'),
                    'confidence': pattern_data.get('confidence', 0.5),
                    'sample_count': pattern_data.get('sample_count', 1)
                })
        
        # Sort by match score
        pattern_matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Determine strategic classification
        if pattern_matches:
            top_match = pattern_matches[0]
            strategic_classification = top_match['strategy_type']
            overall_confidence = top_match['match_score'] * top_match['confidence']
        else:
            strategic_classification = 'unique_build'
            overall_confidence = 0.2
        
        return {
            'pattern_matches': pattern_matches[:5],  # Top 5 matches
            'confidence': overall_confidence,
            'strategic_classification': strategic_classification,
            'build_analysis': self.analyze_build_characteristics(build_order)
        }
    
    def create_build_signature(self, build_order):
        """Create a strategic signature from build order"""
        # Extract key timings and strategic markers
        signature = {
            'early_game': [step for step in build_order if step['supply'] <= 20],
            'key_timings': [step for step in build_order if self.is_key_building(step['name'])],
            'opening_sequence': build_order[:10] if len(build_order) >= 10 else build_order
        }
        return signature
    
    def is_key_building(self, building_name):
        """Identify strategically important buildings"""
        key_buildings = [
            'Gateway', 'Barracks', 'SpawningPool',
            'Stargate', 'Starport', 'Spire',
            'RoboticsFacility', 'Factory', 'RoachWarren',
            'CyberneticsCore', 'TwilightCouncil', 'DarkShrine',
            'Forge', 'EngineeringBay', 'EvolutionChamber'
        ]
        return building_name in key_buildings
    
    def calculate_pattern_similarity(self, build_sig, pattern_sig):
        """Calculate similarity between build signatures"""
        # Simple similarity based on early game overlap
        if 'early_game' not in build_sig or 'early_game' not in pattern_sig:
            return 0.0
        
        build_units = [step['name'] for step in build_sig['early_game']]
        pattern_units = [step.get('name', step.get('unit', '')) for step in pattern_sig['early_game']]
        
        if not build_units or not pattern_units:
            return 0.0
        
        # Calculate overlap
        build_set = set(build_units)
        pattern_set = set(pattern_units)
        
        intersection = len(build_set.intersection(pattern_set))
        union = len(build_set.union(pattern_set))
        
        similarity = intersection / union if union > 0 else 0.0
        
        # Bonus for timing similarity
        timing_bonus = self.calculate_timing_similarity(build_sig['early_game'], pattern_sig['early_game'])
        
        return min(1.0, similarity + timing_bonus * 0.3)
    
    def calculate_timing_similarity(self, build_early, pattern_early):
        """Calculate timing similarity between builds"""
        # Simplified timing comparison
        if not build_early or not pattern_early:
            return 0.0
        
        # Compare first few key timings
        common_units = []
        for build_step in build_early[:5]:
            for pattern_step in pattern_early[:5]:
                if build_step['name'] == pattern_step.get('name', pattern_step.get('unit', '')):
                    time_diff = abs(build_step['time'] - pattern_step.get('time', 0))
                    if time_diff < 30:  # Within 30 seconds
                        common_units.append(1.0 - (time_diff / 30))
        
        return sum(common_units) / max(5, len(build_early)) if common_units else 0.0
    
    def analyze_build_characteristics(self, build_order):
        """Analyze strategic characteristics of the build"""
        if not build_order:
            return {}
        
        # Extract key metrics
        first_military_time = None
        first_tech_time = None
        first_expand_time = None
        
        military_units = ['Marine', 'Zealot', 'Zergling', 'Stalker', 'Roach', 'Marauder']
        tech_buildings = ['Stargate', 'Starport', 'Spire', 'RoboticsFacility', 'Factory']
        expansion_buildings = ['Nexus', 'CommandCenter', 'Hatchery']
        
        for step in build_order:
            if not first_military_time and step['name'] in military_units:
                first_military_time = step['time']
            if not first_tech_time and step['name'] in tech_buildings:
                first_tech_time = step['time']
            if not first_expand_time and step['name'] in expansion_buildings and step['time'] > 0:
                first_expand_time = step['time']
        
        # Classify build style
        build_style = 'unknown'
        if first_expand_time and first_expand_time < 180:  # Expand within 3 minutes
            build_style = 'economic'
        elif first_military_time and first_military_time < 120:  # Military within 2 minutes
            build_style = 'aggressive'
        elif first_tech_time and first_tech_time < 240:  # Tech within 4 minutes
            build_style = 'tech_focused'
        
        return {
            'build_style': build_style,
            'first_military_timing': first_military_time,
            'first_tech_timing': first_tech_time,
            'first_expand_timing': first_expand_time,
            'total_build_steps': len(build_order),
            'average_step_time': sum(step['time'] for step in build_order) / len(build_order)
        }
    
    def generate_strategic_advice(self, keyword_frequency, win_rate):
        """Generate strategic advice based on historical data"""
        advice = []
        
        # Win rate advice
        if win_rate > 0.7:
            advice.append("✅ Strong matchup - continue current strategies")
        elif win_rate < 0.4:
            advice.append("⚠️ Difficult opponent - consider strategy changes")
        else:
            advice.append("📊 Balanced matchup - adapt based on their opening")
        
        # Strategy-specific advice
        common_terms = [term for term, count in keyword_frequency.most_common(3)]
        
        if 'proxy' in common_terms or 'rush' in common_terms:
            advice.append("🔍 Watch for early aggression and cheese builds")
        if 'mech' in common_terms:
            advice.append("⚙️ Expect mech play - prepare anti-mech strategies")
        if 'air' in common_terms or 'void' in common_terms:
            advice.append("✈️ Likely air-focused player - get anti-air early")
        if 'macro' in common_terms:
            advice.append("📈 Macro-oriented opponent - pressure early or out-macro")
        
        return advice
    
    def analyze_replay(self, replay_data):
        """Comprehensive replay analysis using all learned data"""
        
        # Extract basic game info
        opponent_name = replay_data.get('opponent_name', 'Unknown')
        player_race = replay_data.get('player_race', 'Unknown')
        opponent_race = replay_data.get('opponent_race', 'Unknown')
        map_name = replay_data.get('map', 'Unknown')
        build_order = replay_data.get('build_order', [])
        
        print("=" * 80)
        print("🎮 SC2 STRATEGIC ANALYSIS REPORT")
        print("=" * 80)
        print(f"📊 Opponent: {opponent_name} ({opponent_race})")
        print(f"🗺️  Map: {map_name}")
        print(f"👤 Your Race: {player_race}")
        print(f"🔨 Build Order Steps: {len(build_order)}")
        print()
        
        # Opponent Intelligence Analysis
        print("🧠 OPPONENT INTELLIGENCE")
        print("-" * 40)
        
        opponent_intel = self.analyze_opponent_intelligence(opponent_name)
        
        if opponent_intel['known_opponent']:
            print(f"✅ Known opponent ({opponent_intel['games_played']} games)")
            print(f"📈 Historical win rate: {opponent_intel['win_rate']:.1%}")
            print(f"🎯 Intelligence confidence: {opponent_intel['confidence']:.1%}")
            print()
            
            print("📋 Common strategies:")
            for strategy, count in opponent_intel['common_strategies']:
                print(f"   • {strategy} ({count}x)")
            print()
            
            print("💡 Strategic advice:")
            for advice in opponent_intel['strategic_advice']:
                print(f"   {advice}")
            print()
            
            if opponent_intel['recent_games']:
                print("🕐 Recent games:")
                for game in opponent_intel['recent_games'][:3]:
                    result_emoji = "✅" if game['result'] == 'Victory' else "❌"
                    print(f"   {result_emoji} {game['date'][:10]} on {game['map']}: \"{game['comment'][:50]}...\"")
        else:
            print("❓ Unknown opponent - no historical data available")
            print("🎯 Confidence: Low (0%)")
        
        print("\n" + "=" * 80)
        
        # Build Order Pattern Analysis
        print("🏗️ BUILD ORDER PATTERN ANALYSIS")
        print("-" * 40)
        
        pattern_analysis = self.analyze_build_order_patterns(build_order, player_race)
        
        print(f"🔍 Strategic classification: {pattern_analysis['strategic_classification']}")
        print(f"🎯 Pattern confidence: {pattern_analysis['confidence']:.1%}")
        print()
        
        if pattern_analysis['pattern_matches']:
            print("📊 Similar learned patterns:")
            for i, match in enumerate(pattern_analysis['pattern_matches'][:3]):
                print(f"   {i+1}. {match['strategy_type']} (similarity: {match['match_score']:.1%})")
                print(f"      Keywords: {', '.join(match['keywords'][:5])}")
                print(f"      Seen {match['sample_count']}x, confidence: {match['confidence']:.1%}")
                print()
        else:
            print("❓ No similar patterns found - unique build order")
        
        # Build Characteristics
        build_chars = pattern_analysis.get('build_analysis', {})
        if build_chars:
            print("⚙️ Build characteristics:")
            print(f"   Style: {build_chars.get('build_style', 'unknown')}")
            if build_chars.get('first_military_timing'):
                print(f"   First military: {build_chars['first_military_timing']}s")
            if build_chars.get('first_tech_timing'):
                print(f"   First tech: {build_chars['first_tech_timing']}s")
            if build_chars.get('first_expand_timing'):
                print(f"   First expand: {build_chars['first_expand_timing']}s")
        
        print("\n" + "=" * 80)
        
        # Overall Strategic Assessment
        print("🎯 STRATEGIC ASSESSMENT")
        print("-" * 40)
        
        overall_confidence = (
            opponent_intel['confidence'] * 0.6 + 
            pattern_analysis['confidence'] * 0.4
        )
        
        print(f"📊 Overall analysis confidence: {overall_confidence:.1%}")
        print()
        
        # Generate recommendations
        recommendations = []
        
        if opponent_intel['known_opponent'] and opponent_intel['win_rate'] < 0.5:
            recommendations.append("⚠️ Consider strategy adjustment - low historical success rate")
        
        if pattern_analysis['strategic_classification'] in ['aggressive_opening', 'all_in']:
            recommendations.append("🛡️ Prepare for early pressure - prioritize defense")
        elif pattern_analysis['strategic_classification'] == 'economic_opening':
            recommendations.append("💰 Economic build detected - pressure early or out-macro")
        
        if overall_confidence < 0.4:
            recommendations.append("❓ Limited strategic intelligence - adapt based on scouting")
        
        if recommendations:
            print("💡 Strategic recommendations:")
            for rec in recommendations:
                print(f"   {rec}")
        else:
            print("✅ Execute standard gameplan with confidence")
        
        print("\n" + "=" * 80)
        
        return {
            'opponent_intelligence': opponent_intel,
            'pattern_analysis': pattern_analysis,
            'overall_confidence': overall_confidence,
            'recommendations': recommendations
        }

def main():
    # Example usage with sample replay data
    analyzer = SC2ReplayAnalyzer()
    
    # Example 1: Known opponent analysis
    print("🔍 EXAMPLE 1: Analyzing known opponent")
    sample_replay = {
        'opponent_name': 'IIIIIIIIIIII',  # Barcode player from your data
        'opponent_race': 'Protoss',
        'player_race': 'Zerg',
        'map': 'Ley Lines',
        'build_order': [
            {'supply': 12, 'name': 'Drone', 'time': 0},
            {'supply': 13, 'name': 'Overlord', 'time': 12},
            {'supply': 14, 'name': 'Drone', 'time': 17},
            {'supply': 15, 'name': 'SpawningPool', 'time': 35},
            {'supply': 16, 'name': 'Drone', 'time': 40},
            {'supply': 17, 'name': 'Extractor', 'time': 50},
            {'supply': 18, 'name': 'Zergling', 'time': 65},
            {'supply': 20, 'name': 'Zergling', 'time': 68},
        ]
    }
    
    result = analyzer.analyze_replay(sample_replay)
    
    print("\n\n🔍 EXAMPLE 2: Analyzing unknown opponent")
    unknown_replay = {
        'opponent_name': 'RandomPlayer123',
        'opponent_race': 'Terran', 
        'player_race': 'Protoss',
        'map': 'Ancient Cistern',
        'build_order': [
            {'supply': 12, 'name': 'Probe', 'time': 0},
            {'supply': 13, 'name': 'Probe', 'time': 17},
            {'supply': 14, 'name': 'Pylon', 'time': 25},
            {'supply': 15, 'name': 'Gateway', 'time': 43},
            {'supply': 16, 'name': 'Assimilator', 'time': 46},
            {'supply': 19, 'name': 'CyberneticsCore', 'time': 92},
            {'supply': 27, 'name': 'Stargate', 'time': 155},
            {'supply': 29, 'name': 'Oracle', 'time': 190},
        ]
    }
    
    analyzer.analyze_replay(unknown_replay)

if __name__ == "__main__":
    main()
