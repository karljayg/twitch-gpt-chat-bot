import logging
import json
import re
from typing import Tuple, Optional, Dict, Any
from core.interfaces import ILanguageModel
from api.pattern_learning import SC2PatternLearner

logger = logging.getLogger(__name__)

class PatternLearningService:
    def __init__(self, llm: ILanguageModel, pattern_learner: SC2PatternLearner):
        self.llm = llm
        self.pattern_learner = pattern_learner

    async def interpret_user_response(self, user_message: str, ctx: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """
        Process natural language response for pattern learning using LLM to interpret intent
        Returns: tuple (action, comment_text) where action is 'use_pattern', 'use_ai_summary', 'custom', or 'skip'
        """
        try:
            # Construct context strings
            pattern_match = ctx.get('pattern_match')
            ai_summary = ctx.get('ai_summary')
            opponent_name = ctx.get('opponent_name', 'Unknown')
            pattern_similarity = ctx.get('pattern_similarity', 0)

            pattern_text = f"Pattern Match ({pattern_similarity:.0f}%): \"{pattern_match}\"" if pattern_match else "No pattern match"
            ai_text = f"AI Summary: \"{ai_summary}\"" if ai_summary else "No AI summary"
            
            prompt = f"""You are interpreting a user's response for StarCraft 2 build order labeling.

Context:
- Opponent: {opponent_name}
- {pattern_text}
- {ai_text}

User's response: "{user_message}"

Determine the user's intent and respond with ONLY valid JSON (use double quotes):

1. If choosing pattern match AS-IS (keywords: first, 1, pattern, yes it's right, pattern is correct):
   {{"action": "use_pattern"}}

2. If choosing AI summary AS-IS (keywords: second, 2, AI is right, AI summary is correct):
   {{"action": "use_ai_summary"}}

3. If user REFINES option 1 or 2 with additional details (keywords: "but", "except", "actually", "close but", "pretty close" + extra description):
   {{"action": "custom", "text": "<extract the refined/corrected description from user's message>"}}
   Example: "2nd is close but it was roach rush" → {{"action": "custom", "text": "roach rush"}}

4. If providing completely custom description (descriptive text without choosing option 1 or 2):
   {{"action": "custom", "text": "<extract the strategy description>"}}

5. If declining/skipping (keywords: skip, no, neither, ignore, pass):
   {{"action": "skip"}}

CRITICAL: Respond with VALID JSON using double quotes, not single quotes.
Respond ONLY with JSON on one line. No explanation, no markdown."""
            
            # Call LLM - Using generate_raw to bypass persona injection for system-level parsing
            try:
                response = await self.llm.generate_raw(prompt)
            except AttributeError:
                # Fallback for mocks or implementations without generate_raw
                response = await self.llm.generate_response(prompt)
            
            if not response:
                logger.debug("No response from LLM for pattern learning interpretation")
                return ('skip', None)
            
            # Clean response - remove markdown code blocks if present
            response_clean = response.strip()
            response_clean = re.sub(r'^```json?\s*', '', response_clean, flags=re.IGNORECASE)
            response_clean = re.sub(r'\s*```$', '', response_clean)
            response_clean = response_clean.strip()
            
            # Extract just the JSON object (in case LLM adds extra text after)
            # Look for the first { and find its matching }
            json_start = response_clean.find('{')
            if json_start != -1:
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(response_clean)):
                    if response_clean[i] == '{':
                        brace_count += 1
                    elif response_clean[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end != -1:
                    response_clean = response_clean[json_start:json_end]
                    logger.debug(f"Extracted JSON object: {response_clean}")
            
            # Try to parse JSON
            parsed = None
            try:
                parsed = json.loads(response_clean)
            except json.JSONDecodeError as je:
                logger.warning(f"JSON parse error: {je}. Attempting to fix malformed JSON.")
                # Try to fix common issues: single quotes, missing quotes on keys/values
                try:
                    # Simple approach: Force OpenAI's common malformed patterns into valid JSON
                    
                    # Replace single quotes with double quotes first
                    fixed = response_clean.replace("'", '"')
                    
                    # Try to extract action and text using regex patterns
                    action_match = re.search(r'action\s*:\s*([^,}]+)', fixed, re.IGNORECASE)
                    text_match = re.search(r'text\s*:\s*(.+?)\s*}', fixed, re.IGNORECASE)
                    
                    if action_match:
                        action_value = action_match.group(1).strip().strip('"').strip("'")
                        result = {"action": action_value}
                        
                        if text_match:
                            text_value = text_match.group(1).strip().strip('"').strip("'")
                            result["text"] = text_value
                        
                        logger.debug(f"Extracted from malformed JSON: {result}")
                        parsed = result
                    else:
                        # Fallback: try standard fixes
                        fixed = re.sub(r'(\{|,)\s*([a-zA-Z_]+)\s*:', r'\1"\2":', fixed)
                        parsed = json.loads(fixed)
                    
                    if parsed:
                        logger.debug(f"Successfully parsed after fixing: {parsed}")
                except Exception as fix_error:
                    logger.error(f"Could not fix malformed JSON: {fix_error}. Original: {response_clean}")
                    return ('skip', None)
            
            if not parsed:
                return ('skip', None)
            
            action = parsed.get('action', 'skip')
            
            if action == 'use_pattern' and pattern_match:
                return ('use_pattern', pattern_match)
            elif action == 'use_ai_summary' and ai_summary:
                return ('use_ai_summary', ai_summary)
            elif action == 'custom':
                custom_text = parsed.get('text', '').strip()
                if not custom_text:
                    # Fallback: extract anything descriptive from user message
                    custom_text = user_message.strip()
                return ('custom', custom_text)
            else:
                # Default to skip if uncertain or no valid option
                logger.debug(f"Pattern learning response defaulting to skip: {parsed.get('reason', 'no valid option')}")
                return ('skip', None)
                
        except Exception as e:
            logger.error(f"Error processing natural language pattern response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Default to skip on any error
            return ('skip', None)

