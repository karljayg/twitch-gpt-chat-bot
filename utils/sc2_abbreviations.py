#!/usr/bin/env python3
"""
SC2 Build Order Abbreviation Utilities
Provides functions to abbreviate unit/building/upgrade names for Twitch chat readability
"""

from settings import config


def abbreviate_unit_name(unit_name):
    """
    Abbreviate a single unit/building/upgrade name using config.UNIT_ABBREVIATIONS
    
    Args:
        unit_name (str): Full unit/building/upgrade name (e.g., "Siege Tank")
    
    Returns:
        str: Abbreviated name (e.g., "Tank") or original if no abbreviation exists
    """
    return config.UNIT_ABBREVIATIONS.get(unit_name, unit_name)


def abbreviate_build_order(build_order_list, replace_workers_after=5):
    """
    Abbreviate a build order list for Twitch chat readability
    
    Rules:
    - First N workers are kept as abbreviations (SCV/Probe/Drone)
    - After N workers, replace subsequent workers with "-" placeholder
    - All other units/buildings/upgrades get abbreviated per config.UNIT_ABBREVIATIONS
    
    Args:
        build_order_list (list): List of dicts with 'name' key, e.g., [{'name': 'Probe', 'time': 0}, ...]
        replace_workers_after (int): Number of initial workers to show before replacing with "-"
    
    Returns:
        list: List of dicts with abbreviated names
    """
    workers = {'SCV', 'Probe', 'Drone'}
    worker_count = 0
    abbreviated = []
    
    for step in build_order_list:
        unit_name = step.get('name', '')
        
        # Check if this is a worker
        if unit_name in workers:
            worker_count += 1
            
            if worker_count <= replace_workers_after:
                # Keep first N workers as abbreviated names
                abbreviated_step = step.copy()
                abbreviated_step['name'] = abbreviate_unit_name(unit_name)
                abbreviated.append(abbreviated_step)
            else:
                # Replace subsequent workers with "-"
                abbreviated_step = step.copy()
                abbreviated_step['name'] = '-'
                abbreviated.append(abbreviated_step)
        else:
            # Not a worker, apply normal abbreviation
            abbreviated_step = step.copy()
            abbreviated_step['name'] = abbreviate_unit_name(unit_name)
            abbreviated.append(abbreviated_step)
    
    return abbreviated


def format_build_order_for_chat(build_order_list, max_items=15):
    """
    Format an abbreviated build order list as a readable string for Twitch chat
    
    Args:
        build_order_list (list): List of dicts with 'name', 'supply', 'time' keys
        max_items (int): Maximum number of items to include
    
    Returns:
        str: Formatted build order string, e.g., "12 Probe, 13 OL, 14 Pylon, -, -, Gate, Cyber"
    """
    # Abbreviate the build order first
    abbreviated = abbreviate_build_order(build_order_list)
    
    # Take first max_items
    limited = abbreviated[:max_items]
    
    # Format as: "supply unit, supply unit, ..."
    parts = []
    for step in limited:
        supply = step.get('supply', '')
        name = step.get('name', '')
        
        # Don't show supply for workers after replacement (just "-")
        if name == '-':
            parts.append('-')
        else:
            parts.append(f"{supply} {name}")
    
    return ", ".join(parts)


def abbreviate_build_order_string(build_text):
    """
    Apply abbreviations to a build order text string (for use with existing formatted text)
    
    Args:
        build_text (str): Build order as text, e.g., "Siege Tank, Dark Templar, Metabolic Boost"
    
    Returns:
        str: Abbreviated text, e.g., "Tank, DT, Ling Speed"
    """
    # Replace all known unit names with abbreviations
    result = build_text
    
    # Sort by length (longest first) to avoid partial replacements
    # e.g., replace "Siege Tank" before "Tank" to avoid "Siege Tank" becoming "Siege Tank"
    sorted_abbrevs = sorted(config.UNIT_ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for full_name, abbrev in sorted_abbrevs:
        result = result.replace(full_name, abbrev)
    
    return result


