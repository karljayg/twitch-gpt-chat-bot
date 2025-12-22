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


def abbreviate_build_order(build_order_list, show_workers=2, skip_workers_after=True):
    """
    Abbreviate a build order list for Twitch chat readability
    
    Rules:
    - First N workers are kept as abbreviations (SCV/Probe/Drone)
    - After N workers, skip them entirely (don't clutter with useless info)
    - All other units/buildings/upgrades get abbreviated per config.UNIT_ABBREVIATIONS
    - Also skips Overlords after the first one (supply units clutter the preview)
    
    Args:
        build_order_list (list): List of dicts with 'name' key, e.g., [{'name': 'Probe', 'time': 0}, ...]
        show_workers (int): Number of initial workers to show before skipping
        skip_workers_after (bool): If True, skip workers after show_workers limit; if False, show "-"
    
    Returns:
        list: List of dicts with abbreviated names (workers after limit are excluded)
    """
    workers = {'SCV', 'Probe', 'Drone'}
    supply_units = {'Overlord', 'SupplyDepot', 'Pylon'}  # Skip after first appearance
    worker_count = 0
    supply_seen = set()
    abbreviated = []
    
    for step in build_order_list:
        unit_name = step.get('name', '')
        
        # Check if this is a worker
        if unit_name in workers:
            worker_count += 1
            
            if worker_count <= show_workers:
                # Keep first N workers as abbreviated names
                abbreviated_step = step.copy()
                abbreviated_step['name'] = abbreviate_unit_name(unit_name)
                abbreviated.append(abbreviated_step)
            elif not skip_workers_after:
                # Show "-" placeholder (legacy behavior)
                abbreviated_step = step.copy()
                abbreviated_step['name'] = '-'
                abbreviated.append(abbreviated_step)
            # else: skip workers entirely after limit
        elif unit_name in supply_units:
            # Show first supply unit of each type, skip rest
            if unit_name not in supply_seen:
                supply_seen.add(unit_name)
                abbreviated_step = step.copy()
                abbreviated_step['name'] = abbreviate_unit_name(unit_name)
                abbreviated.append(abbreviated_step)
            # else: skip duplicate supply units
        else:
            # Not a worker or supply, apply normal abbreviation
            abbreviated_step = step.copy()
            abbreviated_step['name'] = abbreviate_unit_name(unit_name)
            abbreviated.append(abbreviated_step)
    
    return abbreviated


def format_build_order_for_chat(build_order_list, max_items=15, show_workers=2):
    """
    Format an abbreviated build order list as a readable string for Twitch chat
    
    Shows first N workers, then only important buildings/upgrades/units.
    Workers after the limit are skipped entirely to show meaningful info.
    
    Args:
        build_order_list (list): List of dicts with 'name', 'supply', 'time' keys
        max_items (int): Maximum number of items to include in output
        show_workers (int): Number of initial workers to show before skipping
    
    Returns:
        str: Formatted build order string, e.g., "12 Probe, 14 Pylon, Gate, Cyber, Gas"
    """
    # Abbreviate the build order (filters out workers after limit)
    abbreviated = abbreviate_build_order(build_order_list, show_workers=show_workers)
    
    # Take first max_items
    limited = abbreviated[:max_items]
    
    # Format as: "supply unit, supply unit, ..."
    parts = []
    for step in limited:
        supply = step.get('supply', '')
        name = step.get('name', '')
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


