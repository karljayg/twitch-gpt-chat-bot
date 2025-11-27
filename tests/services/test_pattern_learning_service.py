import pytest
from unittest.mock import MagicMock, AsyncMock
from core.interfaces import ILanguageModel
from api.pattern_learning import SC2PatternLearner

# We'll define the class here first or import it once created
# from core.pattern_learning_service import PatternLearningService

# For TDD, I'll define the expected interface in the test file initially or just mock it
# But ideally I should write the test assuming the class exists in its target location.

@pytest.fixture
def mock_llm():
    # Don't use spec - we want to control which methods exist
    llm = MagicMock()
    # generate_raw doesn't exist, so AttributeError will trigger fallback to generate_response
    # generate_response should be AsyncMock that returns a string
    llm.generate_response = AsyncMock()
    # Explicitly remove generate_raw so AttributeError is raised
    if hasattr(llm, 'generate_raw'):
        delattr(llm, 'generate_raw')
    return llm

@pytest.fixture
def mock_legacy_learner():
    return MagicMock(spec=SC2PatternLearner)

# I'll create the service class structure in a separate file shortly.
# For now, I'm writing the test that *requires* it.

from core.pattern_learning_service import PatternLearningService

@pytest.mark.asyncio
async def test_interpret_user_response_valid_json(mock_llm, mock_legacy_learner):
    service = PatternLearningService(mock_llm, mock_legacy_learner)
    
    # Setup LLM to return valid JSON
    mock_llm.generate_response.return_value = '{"action": "use_pattern"}'
    
    context = {
        'opponent_name': 'TestOpponent',
        'pattern_match': 'Zerg Rush',
        'ai_summary': 'Early Aggression',
        'pattern_similarity': 85
    }
    
    action, text = await service.interpret_user_response("Yes correct", context)
    
    assert action == "use_pattern"
    assert text == "Zerg Rush"

@pytest.mark.asyncio
async def test_interpret_user_response_with_extra_text(mock_llm, mock_legacy_learner):
    service = PatternLearningService(mock_llm, mock_legacy_learner)
    
    # Setup LLM to return JSON with extra text (the bug we fixed)
    mock_llm.generate_response.return_value = '{"action": "use_ai_summary"} TwitchVotes'
    
    context = {
        'opponent_name': 'TestOpponent',
        'pattern_match': 'Zerg Rush',
        'ai_summary': 'Early Aggression',
        'pattern_similarity': 85
    }
    
    action, text = await service.interpret_user_response("Use AI", context)
    
    assert action == "use_ai_summary"
    # The text returned by LLM logic is None for this action, but let's verify it parsed
    
@pytest.mark.asyncio
async def test_interpret_user_response_custom_text(mock_llm, mock_legacy_learner):
    service = PatternLearningService(mock_llm, mock_legacy_learner)
    
    mock_llm.generate_response.return_value = '{"action": "custom", "text": "It was actually a bane bust"}'
    
    context = {} # Context matters less here
    
    action, text = await service.interpret_user_response("No it was bane bust", context)
    
    assert action == "custom"
    assert text == "It was actually a bane bust"

@pytest.mark.asyncio
async def test_interpret_user_response_malformed_json_recovery(mock_llm, mock_legacy_learner):
    service = PatternLearningService(mock_llm, mock_legacy_learner)
    
    # Single quotes instead of double quotes
    mock_llm.generate_response.return_value = "{'action': 'skip'}"
    
    context = {}
    
    action, text = await service.interpret_user_response("skip", context)
    
    assert action == "skip"


