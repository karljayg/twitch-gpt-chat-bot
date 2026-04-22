"""
Strategy Summary Service - Generates concise strategy summaries after games
Uses pattern matching results + OpenAI for natural language variation
"""
from typing import List, Dict, Optional
import logging

from settings import config

logger = logging.getLogger(__name__)


def _is_streamer_player(name: str) -> bool:
    """True if this replay player is the streamer — we only summarize the opponent."""
    if not name or not str(name).strip():
        return False
    n = str(name).strip().lower()
    nick = getattr(config, "STREAMER_NICKNAME", None)
    if nick and n == str(nick).strip().lower():
        return True
    for a in getattr(config, "SC2_PLAYER_ACCOUNTS", []) or []:
        if n == str(a).strip().lower():
            return True
    for a in getattr(config, "SC2_BARCODE_ACCOUNTS", []) or []:
        if n == str(a).strip().lower():
            return True
    return False


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


def _get_top_pattern_match(player_name: str, build_order: List[Dict],
                           pattern_matcher, player_race: str) -> tuple:
    """
    Best pattern match for this build, without a minimum similarity gate.
    Used for post-game lines so we can show unit lists for everyone and only
    attach Pattern: labels when similarity is high enough (see config).
    """
    if not build_order or not pattern_matcher:
        return None, 0.0

    if not player_race or player_race == 'Unknown':
        logger.warning(f"Cannot match patterns for {player_name} - unknown race")
        return None, 0.0

    try:
        matches = pattern_matcher.match_build_against_all_patterns(
            build_order, player_race, logger
        )
        if matches:
            top = matches[0]
            sim = float(top.get('similarity', 0))
            comment = top.get('comment')
            logger.info(
                f"[REPLAY] Top match for {player_name}: '{comment}' at {sim:.2f}"
            )
            return comment, sim
        return None, 0.0
    except Exception as e:
        logger.warning(f"Error matching patterns for {player_name}: {e}")
        return None, 0.0


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
        
        return None, 0.0
        
    except Exception as e:
        logger.warning(f"Error matching patterns for {player_name}: {e}")
        return None, 0


def generate_strategy_summary(player_strategies: Dict[str, tuple]) -> str:
    """
    Combine per-player deterministic lines (units + optional pattern label).
    
    Uses the reusable summarize_strategy_with_units function which combines
    pattern context with real units for accurate, non-hallucinated summaries.
    
    Args:
        player_strategies: Dict of {player_name: (strategy_name, is_winner, key_units, similarity)}
        
    Returns:
        Concise summary string combining all players
    """
    if not player_strategies:
        return ""
    
    from api.chat_utils import summarize_strategy_with_units
    
    # Generate summary for each player using the reusable function
    player_summaries = []
    for player, data in player_strategies.items():
        similarity = None
        if len(data) >= 4:
            strategy, is_winner, key_units, similarity = data[:4]
        elif len(data) == 3:
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
            similarity=similarity,
            logger=logger
        )
        if summary:
            player_summaries.append(summary)

    if not player_summaries:
        return ""

    # Combine player summaries
    if len(player_summaries) == 1:
        return player_summaries[0]
    elif len(player_summaries) == 2:
        return f"{player_summaries[0]}, while {player_summaries[1]}"
    else:
        return " | ".join(player_summaries)


def summarize_game_strategies(players_data: List[Dict], pattern_matcher,
                              max_players: int = 2) -> str:
    """
    Main entry point - summarize strategies for all players in a game.
    
    Args:
        players_data: List of dicts with keys:
            - 'name': player name
            - 'build_order': list of build steps
            - 'race': player's race
        pattern_matcher: MLOpponentAnalyzer instance
        max_players: Maximum number of players to include in summary (default 2 for team games)
    
    Returns:
        Concise strategy summary string, or empty string if no players have build orders
    
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

        if _is_streamer_player(name):
            logger.debug(f"Skipping strategy line for streamer account: {name}")
            continue
        
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
        
        strategy, similarity = _get_top_pattern_match(
            name, build_order, pattern_matcher, race
        )
        if strategy:
            logger.info(f"Strategy match for {name} ({race}): '{strategy}' at {similarity:.2f}")
        else:
            logger.debug(f"No pattern label for {name} ({race}); still including unit summary")

        label = strategy if strategy else ""
        player_matches.append((name, label, similarity, is_winner, key_units[:10]))
    
    if not player_matches:
        logger.debug("No players with build orders for strategy summary")
        return ""
    
    # Sort by similarity (highest first) and take top N
    player_matches.sort(key=lambda x: x[2], reverse=True)
    top_matches = player_matches[:max_players]
    
    # Convert to dict for generate_strategy_summary: {name: (strategy, is_winner, key_units, similarity)}
    player_strategies = {
        name: (strategy, is_winner, key_units, similarity)
        for name, strategy, similarity, is_winner, key_units in top_matches
    }
    
    return generate_strategy_summary(player_strategies)


# Convenience function for quick integration
def get_game_summary(replay_data: Dict, pattern_matcher) -> str:
    """
    Convenience wrapper that extracts player data from replay format.
    
    Args:
        replay_data: Dict with 'players' key containing player info
        pattern_matcher: MLOpponentAnalyzer instance
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
    
    return summarize_game_strategies(players_data, pattern_matcher)

