# SC2 Pattern Learning Admin Tool - Specifications

## Overview

A web-based administration interface for managing the SC2 pattern learning system. Allows the streamer to browse, review, edit, and maintain the learned patterns and player comments that power the ML opponent analysis.

---

## Goals

1. **Data Quality Management** - Review and correct mislabeled or corrupted pattern data
2. **Centralized Editing** - Single interface that syncs changes across all data stores (DB + JSON files)
3. **Similarity Review** - Understand how patterns match and identify problematic matches
4. **Build Order Visualization** - See actual game data to verify comments are accurate

---

## User Stories

### As a streamer/admin, I want to:

1. **Browse all learned patterns** so I can see what the system has learned
2. **Search and filter patterns** by opponent name, race, map, date, or comment text
3. **View pattern details** including build order, timings, and key tech buildings
4. **Edit comment text** to fix typos or mislabeled strategies
5. **Delete bad patterns** that are corrupted or wrong
6. **See similarity matches** to understand what a pattern would match against
7. **Flag suspicious patterns** for later review
8. **Bulk operations** to clean up multiple entries at once

---

## Functional Requirements

### FR-1: Pattern Browser

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Display paginated list of all patterns (20-50 per page) | High |
| FR-1.2 | Show summary for each: opponent, race, map, date, comment preview | High |
| FR-1.3 | Show build order step count and key tech buildings | Medium |
| FR-1.4 | Sort by date (newest first), opponent name, or race | Medium |
| FR-1.5 | Color-code by race (Zerg=purple, Terran=red, Protoss=blue) | Low |

### FR-2: Search & Filter

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Full-text search across comment text | High |
| FR-2.2 | Filter by opponent race | High |
| FR-2.3 | Filter by opponent name | Medium |
| FR-2.4 | Filter by map name | Low |
| FR-2.5 | Filter by date range | Low |
| FR-2.6 | Filter by "flagged for review" status | Medium |

### FR-3: Pattern Detail View

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Display full comment text (editable) | High |
| FR-3.2 | Display game metadata (opponent, race, map, date, result, duration) | High |
| FR-3.3 | Display build order as formatted list with timings | High |
| FR-3.4 | Highlight key tech buildings (Roach Warren, Baneling Nest, Stargate, etc.) | High |
| FR-3.5 | Show first expansion timing | Medium |
| FR-3.6 | Display extracted keywords | Low |

### FR-4: Similarity Analysis

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | For selected pattern, show top 5-10 similar patterns with % | High |
| FR-4.2 | Highlight self-match (should be 100%) | High |
| FR-4.3 | Flag patterns where self-match is not 100% | Medium |
| FR-4.4 | Show what tech buildings differ between two patterns | Medium |
| FR-4.5 | Link to click through to similar patterns | Low |

### FR-5: Edit & Save

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Edit comment text inline | High |
| FR-5.2 | Save changes with confirmation | High |
| FR-5.3 | Sync changes to database (player_comments table) | High |
| FR-5.4 | Sync changes to comments.json | High |
| FR-5.5 | Sync changes to patterns.json | High |
| FR-5.6 | Show sync status/errors | Medium |
| FR-5.7 | Audit log of changes (who, when, what changed) | Low |

### FR-6: Delete

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Delete single pattern with confirmation | High |
| FR-6.2 | Cascade delete to all data stores (DB + JSON files) | High |
| FR-6.3 | Bulk delete selected patterns | Medium |
| FR-6.4 | Soft delete option (mark as inactive vs permanent delete) | Low |

### FR-7: Flagging & Review Queue

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | Flag pattern for review | Medium |
| FR-7.2 | Add review notes | Medium |
| FR-7.3 | View review queue (all flagged patterns) | Medium |
| FR-7.4 | Mark as reviewed/resolved | Medium |

### FR-8: Data Integrity

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | Detect patterns with mismatched comment vs build order | High |
| FR-8.2 | Detect patterns with very short build orders (<30 steps) | High |
| FR-8.3 | Detect patterns where self-match is not 100% | Medium |
| FR-8.4 | Generate data quality report | Medium |
| FR-8.5 | Auto-backup before bulk operations | High |

---

## Data Model

### Primary Data Stores

1. **MySQL Database**
   - `player_comments` table - source of truth for comments
   - `sc2_replays` table - game metadata and build orders

2. **comments.json**
   - Cached comments with build order data
   - Used by pattern matching engine

3. **patterns.json**
   - Patterns with signatures for ML matching
   - Derived from comments.json

### Sync Flow

```
┌──────────────────┐
│  Admin Tool UI   │
└────────┬─────────┘
         │ Edit/Delete
         ▼
┌──────────────────┐
│  MySQL Database  │  ← Source of Truth
└────────┬─────────┘
         │ Sync
         ▼
┌──────────────────┐
│  comments.json   │  ← Pattern Learning
└────────┬─────────┘
         │ Regenerate
         ▼
┌──────────────────┐
│  patterns.json   │  ← ML Analysis
└──────────────────┘
```

---

## UI Wireframes

### Main List View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SC2 Pattern Learning Admin                                    [Logout] │
├─────────────────────────────────────────────────────────────────────────┤
│ Search: [_______________]  Race: [All ▼]  Status: [All ▼]  [Search]     │
├─────────────────────────────────────────────────────────────────────────┤
│ Showing 1-20 of 300 patterns                          [< Prev] [Next >] │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ #1 | Bjorn (Zerg) | White Rabbit LE | 2025-11-25                    │ │
│ │ "pool first ling bane all in"                                       │ │
│ │ 60 steps | SpawningPool@57s, BaneNest@?                             │ │
│ │ Similar: 88% roach ling | 77% ling flood | 65% proxy rax            │ │
│ │ [View] [Edit] [Delete] [Flag]                                       │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ #2 | Darkblade (Protoss) | Ley Lines | 2025-01-07                   │ │
│ │ "pylon block to Nexus first. he gg'd after seeing my pool first"    │ │
│ │ 9 steps | Nexus@?                                                    │ │
│ │ Similar: 100% (SELF) | 16% chargelot all in                         │ │
│ │ [View] [Edit] [Delete] [Flag]                                       │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│ ...                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detail View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Pattern #1 Details                                      [Back to List] │
├─────────────────────────────────────────────────────────────────────────┤
│ GAME INFO                                                               │
│ ─────────────────────────────────────────────────────────────────────── │
│ Opponent: Bjorn                                                         │
│ Race: Zerg                                                              │
│ Map: White Rabbit LE                                                    │
│ Date: 2025-11-25 23:58:25                                               │
│ Result: Win | Duration: 8:42                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ COMMENT                                                         [Edit]  │
│ ─────────────────────────────────────────────────────────────────────── │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ pool first ling bane all in                                         │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│ Keywords: pool, ling, bane, all in                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ BUILD ORDER (60 steps)                                                  │
│ ─────────────────────────────────────────────────────────────────────── │
│  1. 0:00  Drone (12)                                                    │
│  2. 0:12  Drone (13)                                                    │
│  3. 0:19  Overlord (14)                                                 │
│  ...                                                                    │
│  9. 0:57  SpawningPool (17) ★ KEY                                       │
│ 13. 1:31  Hatchery (19) ★ EXPANSION                                     │
│ 21. 2:11  RoachWarren (24) ★ KEY                                        │
│ ...                                                                     │
│ ⚠️ WARNING: Comment mentions "bane" but BanelingNest not found!         │
├─────────────────────────────────────────────────────────────────────────┤
│ SIMILAR PATTERNS                                                        │
│ ─────────────────────────────────────────────────────────────────────── │
│ 1. 100% - "pool first ling bane all in" (SELF)                          │
│ 2.  88% - "ling roach all in" → [View]                                  │
│ 3.  88% - "roach ling all in" → [View]                                  │
│ 4.  77% - "roach/ling all in" → [View]                                  │
│ 5.  65% - "proxy rax roaches" → [View]                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                              [Save Changes] [Delete Pattern]            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Quality Report

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Data Quality Report                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ SUMMARY                                                                 │
│ ─────────────────────────────────────────────────────────────────────── │
│ Total Patterns: 300                                                     │
│ Perfect Self-Match (100%): 294 ✓                                        │
│ High Self-Match (90-99%): 1                                             │
│ Low Self-Match (<90%): 5 ⚠️                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ ISSUES DETECTED                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│ ⚠️ 24 patterns mention tech not in build order                          │
│    [View List]                                                          │
│                                                                         │
│ ⚠️ 2 patterns have very short builds (<30 steps)                        │
│    [View List]                                                          │
│                                                                         │
│ ⚠️ 5 patterns have low self-match score                                 │
│    [View List]                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ ACTIONS                                                                 │
│ ─────────────────────────────────────────────────────────────────────── │
│ [Run Full Verification] [Export Report] [Backup Data]                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Non-Functional Requirements

### NFR-1: Performance
- Page load time < 2 seconds
- Search results < 1 second
- Pattern similarity calculation cached

### NFR-2: Security
- Password protected (single admin user)
- Local network access only (or VPN)
- No public internet exposure

### NFR-3: Reliability
- Auto-backup before any delete/bulk operation
- Transaction-safe database updates
- Graceful error handling with rollback

### NFR-4: Usability
- Mobile-friendly responsive design
- Keyboard shortcuts for common actions
- Confirmation dialogs for destructive actions

---

## Implementation Options

### Option A: Python Flask
- **Pros**: Same language as bot, easy integration, familiar
- **Cons**: Need to learn Flask if not familiar

### Option B: PHP
- **Pros**: Simple deployment, mature ecosystem
- **Cons**: Different language from bot, need separate DB connection

### Option C: Node.js/Express
- **Pros**: Modern, fast, good for real-time updates
- **Cons**: Different language, more setup

### Option D: Static HTML + Python Scripts
- **Pros**: Simplest, no server needed
- **Cons**: No real-time editing, regenerate each time

### Recommendation
Flask is recommended for tight integration with existing Python codebase and ability to reuse `MLOpponentAnalyzer` and database utilities.

---

## Future Enhancements

1. **Import from Replay** - Directly import patterns from replay files
2. **AI Suggestions** - Let GPT suggest comment corrections
3. **Pattern Merge** - Combine similar patterns into one
4. **Export/Import** - Backup and restore pattern data
5. **Multi-user** - Support for multiple admins with different permissions
6. **Live Preview** - See how edited comment would match during a game

---

## Appendix: Current Data Files

| File | Purpose | Records |
|------|---------|---------|
| `data/comments.json` | Cached comments with build orders | ~300 |
| `data/patterns.json` | ML patterns with signatures | ~300 |
| `data/learning_stats.json` | Statistics and metrics | N/A |
| Database `player_comments` | Source of truth for comments | ~300 |
| Database `sc2_replays` | Game metadata and build orders | ~1000+ |

---

*Last Updated: 2025-12-19*
*Version: 1.0 Draft*










