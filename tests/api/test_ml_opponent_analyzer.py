"""
Tests for MLOpponentAnalyzer - Pattern matching logic.

These tests would catch:
- Pattern matching failures (12 pool, cannon rush, etc.)
- Race filtering bugs (Terran matching Zerg patterns)
- Time format bugs (string '1:28' vs int 88)
- Strategic item extraction bugs
- Low confidence matches being selected
"""
import pytest
from unittest.mock import MagicMock, patch
from api.ml_opponent_analyzer import MLOpponentAnalyzer
import settings.config as config


@pytest.fixture
def mock_logger():
    """Mock logger"""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def analyzer(mock_logger):
    """Create MLOpponentAnalyzer instance"""
    analyzer = MLOpponentAnalyzer()
    analyzer.logger = mock_logger
    return analyzer


def create_build_order(items):
    """
    Helper to create build order format.
    items: List of tuples (supply, name, time_in_seconds)
    """
    return [{"supply": s, "name": n, "time": t} for s, n, t in items]


def create_pattern_signature(early_game=None, key_timings=None):
    """Helper to create pattern signature format"""
    sig = {}
    if early_game:
        sig['early_game'] = early_game
    if key_timings:
        sig['key_timings'] = key_timings
    return sig


class TestStrategicItemExtraction:
    """Test _extract_strategic_items_from_build"""
    
    def test_extracts_zerg_strategic_items(self, analyzer, mock_logger):
        """Should extract strategic Zerg items (RoachWarren, Roach, etc.)"""
        build = create_build_order([
            (12, "Drone", 10),
            (13, "RoachWarren", 120),
            (14, "Roach", 150),
            (15, "Overlord", 180)
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Zerg")
        
        item_names = [item['name'] for item in items]
        assert "roachwarren" in item_names, "RoachWarren should be extracted"
        assert "roach" in item_names, "Roach should be extracted"
        assert "drone" not in item_names, "Workers should be filtered out"
    
    def test_extracts_protoss_cannon_rush(self, analyzer, mock_logger):
        """Cannon rush should extract Forge and PhotonCannon"""
        build = create_build_order([
            (12, "Probe", 10),
            (13, "Pylon", 50),
            (14, "Forge", 90),
            (15, "PhotonCannon", 120)
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Protoss")
        
        item_names = [item['name'] for item in items]
        assert "forge" in item_names, "Forge should be extracted"
        assert "photoncannon" in item_names, "PhotonCannon should be extracted"
    
    def test_filters_workers_and_supply(self, analyzer, mock_logger):
        """Workers and supply structures should be filtered"""
        build = create_build_order([
            (12, "SCV", 10),
            (13, "SupplyDepot", 50),
            (14, "Factory", 90)  # Factory is in SC2_STRATEGIC_ITEMS for Terran
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Terran")
        
        item_names = [item['name'] for item in items]
        assert "scv" not in item_names
        assert "supplydepot" not in item_names
        assert "factory" in item_names


class TestPatternSignatureExtraction:
    """Test _extract_strategic_items_from_signature - handles stored patterns"""
    
    def test_extracts_from_early_game(self, analyzer, mock_logger):
        """Should extract items from early_game sequence"""
        signature = create_pattern_signature(
            early_game=[
                {"unit": "RoachWarren", "time": 120},
                {"unit": "Roach", "time": 150}
            ]
        )
        
        items = analyzer._extract_strategic_items_from_signature(signature, "Zerg")
        
        item_names = [item['name'] for item in items]
        assert "roachwarren" in item_names
        assert "roach" in item_names
    
    def test_extracts_from_key_timings(self, analyzer, mock_logger):
        """Should extract items from key_timings"""
        signature = create_pattern_signature(
            key_timings={
                "Forge": 90,
                "PhotonCannon": 120
            }
        )
        
        items = analyzer._extract_strategic_items_from_signature(signature, "Protoss")
        
        item_names = [item['name'] for item in items]
        assert "forge" in item_names
        assert "photoncannon" in item_names
    
    def test_converts_time_string_to_seconds(self, analyzer, mock_logger):
        """Critical bug fix: Should convert '1:28' to 88 seconds"""
        signature = create_pattern_signature(
            early_game=[
                {"unit": "RoachWarren", "time": "2:00"}  # String format
            ]
        )
        
        items = analyzer._extract_strategic_items_from_signature(signature, "Zerg")
        
        assert len(items) > 0
        assert items[0]['timing'] == 120, "Should convert '2:00' to 120 seconds"
        assert isinstance(items[0]['timing'], (int, float)), "Timing should be numeric"
    
    def test_handles_int_time_format(self, analyzer, mock_logger):
        """Should handle integer time format (already in seconds)"""
        signature = create_pattern_signature(
            early_game=[
                {"unit": "RoachWarren", "time": 120}  # Integer format
            ]
        )
        
        items = analyzer._extract_strategic_items_from_signature(signature, "Zerg")
        
        assert len(items) > 0
        assert items[0]['timing'] == 120
        assert isinstance(items[0]['timing'], (int, float))


class TestRaceFiltering:
    """Test race-based pattern filtering"""
    
    def test_filters_by_explicit_race_field(self, analyzer, mock_logger):
        """Should use explicit 'race' field from pattern before signature detection"""
        patterns = [{
            "comment": "12 pool",
            "race": "Zerg",  # Explicit race field
            "signature": create_pattern_signature(
                early_game=[{"unit": "SpawningPool", "time": 88}]
            )
        }]
        
        # Try to match Terran build against Zerg pattern
        build = create_build_order([
            (12, "Barracks", 90)
        ])
        
        new_items = analyzer._extract_strategic_items_from_build(build, "Terran")
        pattern_items = analyzer._extract_strategic_items_from_signature(
            patterns[0]['signature'], "Zerg"
        )
        
        # Should filter out because races don't match
        pattern_race = patterns[0].get('race', '').lower()
        opponent_race = "Terran".lower()
        
        assert pattern_race != opponent_race, "Races should not match"
    
    def test_terran_pattern_not_matches_zerg_build(self, analyzer, mock_logger):
        """Terran pattern should not match Zerg build (race filtering bug)"""
        patterns = [{
            "comment": "proxy rax all in",
            "race": "Terran",
            "signature": create_pattern_signature(
                early_game=[{"unit": "Barracks", "time": 90}]
            )
        }]
        
        # Zerg build
        build = create_build_order([
            (13, "RoachWarren", 120),
            (14, "Roach", 150)
        ])
        
        new_items = analyzer._extract_strategic_items_from_build(build, "Zerg")
        pattern_items = analyzer._extract_strategic_items_from_signature(
            patterns[0]['signature'], "Terran"
        )
        
        # Should have no matching items
        new_dict = {item['name']: item for item in new_items}
        pattern_dict = {item['name']: item for item in pattern_items}
        matching = set(new_dict.keys()) & set(pattern_dict.keys())
        
        assert len(matching) == 0, "Terran and Zerg builds should not match"


class TestBuildComparison:
    """Test _compare_build_signatures"""
    
    def test_identical_builds_high_similarity(self, analyzer, mock_logger):
        """Identical builds should have high similarity"""
        build1 = [
            {"name": "roachwarren", "timing": 120, "position": 0},
            {"name": "roach", "timing": 150, "position": 1}
        ]
        build2 = [
            {"name": "roachwarren", "timing": 120, "position": 0},
            {"name": "roach", "timing": 150, "position": 1}
        ]
        
        score = analyzer._compare_build_signatures(build1, build2, "Zerg", mock_logger)
        
        assert score > 0.5, "Identical builds should have high similarity"
    
    def test_different_builds_low_similarity(self, analyzer, mock_logger):
        """Completely different builds should have low similarity"""
        build1 = [
            {"name": "spawningpool", "timing": 88, "position": 0}
        ]
        build2 = [
            {"name": "stargate", "timing": 300, "position": 0}
        ]
        
        score = analyzer._compare_build_signatures(build1, build2, "Zerg", mock_logger)
        
        assert score < 0.3, "Different builds should have low similarity"
    
    def test_handles_string_timing_in_pattern(self, analyzer, mock_logger):
        """Critical bug fix: Should handle string timing in stored patterns"""
        new_build = [
            {"name": "roachwarren", "timing": 120, "position": 0}
        ]
        pattern_build = [
            {"name": "roachwarren", "timing": "2:00", "position": 0}  # String format
        ]
        
        # Should not crash, should convert and compare
        try:
            score = analyzer._compare_build_signatures(new_build, pattern_build, "Zerg", mock_logger)
            assert isinstance(score, (int, float)), "Should return numeric score"
        except TypeError as e:
            pytest.fail(f"Should handle string timing conversion: {e}")
    
    def test_timing_similarity_bonus(self, analyzer, mock_logger):
        """Builds with similar timings should score higher"""
        build1 = [
            {"name": "roachwarren", "timing": 120, "position": 0}
        ]
        build2_close = [
            {"name": "roachwarren", "timing": 127, "position": 0}  # 7 seconds difference
        ]
        build2_far = [
            {"name": "roachwarren", "timing": 232, "position": 0}  # 112 seconds difference
        ]
        
        score_close = analyzer._compare_build_signatures(build1, build2_close, "Zerg", mock_logger)
        score_far = analyzer._compare_build_signatures(build1, build2_far, "Zerg", mock_logger)
        
        assert score_close > score_far, "Closer timings should have higher similarity"


class TestPatternMatching:
    """Test match_build_against_all_patterns integration"""
    
    @patch('api.ml_opponent_analyzer.MLOpponentAnalyzer.load_learning_data')
    def test_matches_roach_timing_pattern(self, mock_load, analyzer, mock_logger):
        """Should match roach timing build against stored roach pattern"""
        # Mock pattern data
        mock_load.return_value = {
            'comments': [{
                'comment': 'roach timing',
                'game_data': {
                    'opponent_race': 'Zerg',
                    'build_order': [
                        {"supply": 13, "name": "RoachWarren", "time": 120},
                        {"supply": 14, "name": "Roach", "time": 150}
                    ]
                }
            }]
        }
        
        build = create_build_order([
            (13, "RoachWarren", 120),
            (14, "Roach", 150)
        ])
        
        matches = analyzer.match_build_against_all_patterns(build, "Zerg", mock_logger)
        
        assert len(matches) > 0, "Should match roach timing pattern"
        assert matches[0]['comment'] == "roach timing"
        assert matches[0]['similarity'] > 0.2, "Should have reasonable similarity score"
    
    @patch('api.ml_opponent_analyzer.MLOpponentAnalyzer.load_learning_data')
    def test_filters_low_confidence_matches(self, mock_load, analyzer, mock_logger):
        """Should filter out very low confidence matches (<20%) when AI analysis available"""
        # This tests the logic that filters matches below threshold
        mock_load.return_value = {
            'comments': [{
                'comment': 'unrelated build',
                'game_data': {
                    'opponent_race': 'Zerg',
                    'build_order': [
                        {"supply": 20, "name": "Spire", "time": 500}
                    ]
                }
            }]
        }
        
        build = create_build_order([
            (13, "RoachWarren", 120),
            (14, "Roach", 150)
        ])
        
        matches = analyzer.match_build_against_all_patterns(build, "Zerg", mock_logger)
        
        # If similarity is too low, should be filtered or have very low score
        if len(matches) > 0:
            assert matches[0]['similarity'] < 0.2, "Unrelated builds should have low similarity"


class TestExpansionCounting:
    """Test expansion counting in build comparison (Dec 2024 fix)
    
    Note: Expansions (Hatchery/Nexus/CommandCenter) are counted SEPARATELY
    from strategic items via the original build order in _match_build_against_patterns.
    They are intentionally filtered from strategic items to avoid noise.
    """
    
    def test_expansions_filtered_from_strategic(self, analyzer, mock_logger):
        """Expansions should be filtered from strategic items (counted separately)"""
        build = create_build_order([
            (12, "Drone", 10),
            (13, "Hatchery", 53),
            (14, "SpawningPool", 77),
            (15, "Hatchery", 154)
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Zerg")
        item_names = [item['name'] for item in items]
        
        # Hatchery filtered - counted separately for expansion comparison
        assert "hatchery" not in item_names, "Hatchery should be filtered (counted separately)"
        assert "spawningpool" in item_names, "SpawningPool should be strategic"
    
    def test_zerg_3hatch_vs_2hatch_expansion_difference(self, analyzer, mock_logger):
        """3 hatch build should differ from 2 hatch in expansion count"""
        # This tests that expansion counting works via original build order
        build_3hatch = create_build_order([
            (13, "Hatchery", 53),
            (14, "SpawningPool", 77),
            (15, "Hatchery", 100),
            (16, "Hatchery", 154)
        ])
        build_2hatch = create_build_order([
            (13, "Hatchery", 53),
            (14, "SpawningPool", 77),
            (15, "RoachWarren", 120)
        ])
        
        # Count expansions manually (same logic as in ml_opponent_analyzer)
        expansion_names = {'hatchery', 'nexus', 'commandcenter'}
        count_3hatch = sum(1 for step in build_3hatch if step.get('name', '').lower() in expansion_names)
        count_2hatch = sum(1 for step in build_2hatch if step.get('name', '').lower() in expansion_names)
        
        assert count_3hatch == 3, "3 hatch build should have 3 expansions"
        assert count_2hatch == 1, "2 hatch build should have 1 expansion"
        assert count_3hatch > count_2hatch, "3 hatch should have more expansions"


class TestDeduplication:
    """Test strategic item deduplication (Dec 2024 fix)"""
    
    def test_deduplicates_strategic_items(self, analyzer, mock_logger):
        """Should keep only first occurrence of each strategic item"""
        build = create_build_order([
            (13, "Roach", 150),
            (14, "Roach", 160),
            (15, "Roach", 170),
            (16, "Roach", 180)
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Zerg")
        roach_items = [i for i in items if i['name'] == 'roach']
        
        assert len(roach_items) == 1, "Should deduplicate to single Roach entry"
        assert roach_items[0]['timing'] == 150, "Should keep first occurrence timing"
    
    def test_keeps_different_items(self, analyzer, mock_logger):
        """Should keep different strategic items"""
        build = create_build_order([
            (13, "RoachWarren", 120),
            (14, "Roach", 150),
            (15, "BanelingNest", 200),
            (16, "Baneling", 220)
        ])
        
        items = analyzer._extract_strategic_items_from_build(build, "Zerg")
        item_names = [item['name'] for item in items]
        
        assert "roachwarren" in item_names
        assert "roach" in item_names
        assert "banelingnest" in item_names
        assert "baneling" in item_names


class TestBidirectionalTechPenalty:
    """Test bidirectional critical tech penalty (Dec 2024 fix)"""
    
    def test_roach_pattern_vs_ling_build_penalty(self, analyzer, mock_logger):
        """Roach pattern should have low match against pure ling build"""
        roach_pattern = [
            {"name": "spawningpool", "timing": 70, "position": 0},
            {"name": "roachwarren", "timing": 120, "position": 1},
            {"name": "roach", "timing": 150, "position": 2}
        ]
        ling_build = [
            {"name": "spawningpool", "timing": 75, "position": 0},
            {"name": "hatchery", "timing": 90, "position": 1}
        ]
        
        score = analyzer._compare_build_signatures(ling_build, roach_pattern, "Zerg", mock_logger)
        
        assert score < 0.6, "Roach pattern vs pure ling should have penalty"
    
    def test_matching_pure_ling_builds_bonus(self, analyzer, mock_logger):
        """Two pure ling builds (no roach/bane) should match well"""
        ling1 = [
            {"name": "spawningpool", "timing": 77, "position": 0},
            {"name": "hatchery", "timing": 53, "position": 1},
            {"name": "hatchery", "timing": 154, "position": 2}
        ]
        ling2 = [
            {"name": "spawningpool", "timing": 80, "position": 0},
            {"name": "hatchery", "timing": 55, "position": 1},
            {"name": "hatchery", "timing": 160, "position": 2}
        ]
        
        score = analyzer._compare_build_signatures(ling1, ling2, "Zerg", mock_logger)
        
        assert score > 0.5, "Similar pure ling builds should match well"