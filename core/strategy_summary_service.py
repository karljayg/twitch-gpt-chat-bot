"""
Strategy Summary Service - Generates concise strategy summaries after games
Uses pattern matching results + OpenAI for natural language variation
"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_strategy_for_player(player_name: str, build_order: List[Dict], 
                            pattern_matcher, opponent_race: str,
                            min_similarity: float = 0.70) -> Optional[str]:
    """
    Get the best matching strategy for a player's build order.
    
    Args:
        player_name: Name of the player
        build_order: List of build order steps
        pattern_matcher: MLOpponentAnalyzer instance
        opponent_race: Race of the opponent (for pattern filtering)
        min_similarity: Minimum similarity threshold (default 70%)
    
    Returns:
        Strategy name if match >= min_similarity, else None
    """
    strategy, _ = _get_strategy_with_score(player_name, build_order, pattern_matcher, opponent_race, min_similarity)
    return strategy


def _get_strategy_with_score(player_name: str, build_order: List[Dict], 
                              pattern_matcher, player_race: str,
                              min_similarity: float = 0.70) -> tuple:
    """
    Get the best matching strategy and similarity score for a player's build order.
    
    Args:
        player_name: Name of the player
        build_order: List of build order steps
        pattern_matcher: MLOpponentAnalyzer instance
        player_race: Race of the player whose build we're analyzing
        min_similarity: Minimum similarity threshold
    
    Returns:
        Tuple of (strategy_name, similarity_score) or (None, 0) if no match
    """
    if not build_order or not pattern_matcher:
        return None, 0
    
    if not player_race or player_race == 'Unknown':
        logger.warning(f"Cannot match patterns for {player_name} - unknown race")
        return None, 0
    
    try:
        logger.info(f"[REPLAY] Matching patterns for {player_name} ({player_race}) with {len(build_order)} build steps")
        
        matches = pattern_matcher.match_build_against_all_patterns(
            build_order, player_race, logger
        )
        
        logger.info(f"[REPLAY] Got {len(matches) if matches else 0} pattern matches")
        
        if matches:
            top_match = matches[0]
            logger.info(f"[REPLAY] Top match for {player_name}: '{top_match['comment']}' at {top_match['similarity']:.2f}")
            if top_match['similarity'] >= min_similarity:
                return top_match['comment'], top_match['similarity']
        
        return None, 0
        
    except Exception as e:
        logger.warning(f"Error matching patterns for {player_name}: {e}")
        return None, 0


def generate_strategy_summary(player_strategies: Dict[str, tuple]) -> str:
    """
    Generate a concise summary of player strategies using OpenAI.
    
    Uses the reusable summarize_strategy_with_units function which combines
    pattern context with real units for accurate, non-hallucinated summaries.
    
    Args:
        player_strategies: Dict of {player_name: (strategy_name, is_winner, key_units)}
        
    Returns:
        Concise summary string combining all players
    """
    if not player_strategies:
        return ""
    
    from api.chat_utils import summarize_strategy_with_units
    
    # Generate summary for each player using the reusable function
    player_summaries = []
    for player, data in player_strategies.items():
        # Handle both old format (strategy, is_winner) and new format (strategy, is_winner, key_units)
        if len(data) == 3:
            strategy, is_winner, key_units = data
        else:
            strategy, is_winner = data
            key_units = []
        
        # Use the reusable function that marries pattern context with real units
        summary = summarize_strategy_with_units(
            player_name=player,
            pattern_name=strategy,
            real_units=key_units,
            is_winner=is_winner,
            logger=logger
        )
        player_summaries.append(summary)
    
    # Combine player summaries
    if len(player_summaries) == 1:
        return player_summaries[0]
    elif len(player_summaries) == 2:
        return f"{player_summaries[0]}, while {player_summaries[1]}"
    else:
        return " | ".join(player_summaries)


def _fallback_summary(player_strategies: Dict[str, tuple]) -> str:
    """Fallback when OpenAI is unavailable
    
    Args:
        player_strategies: Dict of {player_name: (strategy, is_winner, key_units)}
    """
    parts = []
    for player, data in player_strategies.items():
        # Handle both old format (strategy, is_winner) and new format (strategy, is_winner, key_units)
        if len(data) == 3:
            strategy, is_winner, key_units = data
            # Use actual units instead of pattern name
            units_str = ", ".join(key_units[:4]) if key_units else strategy[:30]
        else:
            strategy, is_winner = data
            units_str = strategy[:30]
        
        result = "(W)" if is_winner else "(L)"
        parts.append(f"{player} {result}: {units_str}")
    return " | ".join(parts)


def summarize_game_strategies(players_data: List[Dict], pattern_matcher,
                              min_similarity: float = 0.70,
                              max_players: int = 2) -> str:
    """
    Main entry point - summarize strategies for all players in a game.
    
    Args:
        players_data: List of dicts with keys:
            - 'name': player name
            - 'build_order': list of build steps
            - 'race': player's race
        pattern_matcher: MLOpponentAnalyzer instance
        min_similarity: Minimum match threshold (default 70%)
        max_players: Maximum number of players to include in summary (default 2 for team games)
    
    Returns:
        Concise strategy summary string, or empty string if no high matches
    
    Example:
        players = [
            {'name': 'PlayerA', 'build_order': [...], 'race': 'Zerg'},
            {'name': 'PlayerB', 'build_order': [...], 'race': 'Terran'}
        ]
        summary = summarize_game_strategies(players, ml_analyzer)
        # "PlayerA went baneling bust, PlayerB did bio drop"
    """
    player_matches = []  # List of (name, strategy, similarity, is_winner, key_units)
    
    for player in players_data:
        name = player.get('name', 'Unknown')
        build_order = player.get('build_order', [])
        race = player.get('race', 'Unknown')
        is_winner = player.get('is_winner', False)
        
        logger.info(f"Strategy matching for {name} ({race}): {len(build_order)} build steps")
        
        # Skip if no build order
        if not build_order:
            logger.debug(f"Skipping {name} - no build order")
            continue
        
        # Extract actual key units from build order (exclude workers/supply)
        workers = {'scv', 'probe', 'drone'}
        supply = {'supplydepot', 'pylon', 'overlord', 'overseerdepotlowered'}
        key_units = []
        seen = set()
        for step in build_order:
            unit = step.get('name', '')
            unit_lower = unit.lower()
            if unit_lower not in workers and unit_lower not in supply and unit_lower not in seen:
                key_units.append(unit)
                seen.add(unit_lower)
        
        # Get strategy with similarity score
        strategy, similarity = _get_strategy_with_score(
            name, build_order, pattern_matcher, race, min_similarity
        )
        
        if strategy:
            logger.info(f"Strategy match for {name} ({race}): '{strategy}' at {similarity:.2f}")
            player_matches.append((name, strategy, similarity, is_winner, key_units[:10]))
    
    if not player_matches:
        logger.debug("No players with high-confidence strategy matches")
        return ""
    
    # Sort by similarity (highest first) and take top N
    player_matches.sort(key=lambda x: x[2], reverse=True)
    top_matches = player_matches[:max_players]
    
    # Convert to dict for generate_strategy_summary: {name: (strategy, is_winner, key_units)}
    player_strategies = {name: (strategy, is_winner, key_units) for name, strategy, _, is_winner, key_units in top_matches}
    
    return generate_strategy_summary(player_strategies)


# Convenience function for quick integration
def get_game_summary(replay_data: Dict, pattern_matcher, 
                     min_similarity: float = 0.70) -> str:
    """
    Convenience wrapper that extracts player data from replay format.
    
    Args:
        replay_data: Dict with 'players' key containing player info
        pattern_matcher: MLOpponentAnalyzer instance
        min_similarity: Minimum match threshold
    
    Returns:
        Strategy summary string including win/loss info
    """
    players = replay_data.get('players', {})
    
    players_data = []
    for player_key, player_info in players.items():
        name = player_info.get('name', 'Unknown')
        race = player_info.get('race', 'Unknown')
        build_order = player_info.get('buildOrder', [])
        
        logger.debug(f"Player {name}: race={race}, build_order_steps={len(build_order)}")
        
        players_data.append({
            'name': name,
            'build_order': build_order,
            'race': race,
            'is_winner': player_info.get('is_winner', False)
        })
    
    return summarize_game_strategies(players_data, pattern_matcher, min_similarity)

