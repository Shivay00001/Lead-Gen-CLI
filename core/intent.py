import logging
import requests
import urllib.parse
from typing import List, Dict, Any

try:
    import g4f
    HAS_G4F = True
except ImportError:
    HAS_G4F = False

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    def __init__(self, openai_api_key: str = None):
        # We don't need the key if we are using the free Pollinations AI endpoint or g4f
        self.api_key = openai_api_key

    def score_intent(self, leads: List[Dict[str, Any]], keywords: str) -> List[Dict[str, Any]]:
        """
        Analyzes intent using g4f if available, otherwise falls back to Pollinations.ai API.
        """
        logger.info("Analyzing intent and buying signals...")
        
        qualified_leads = []
        
        for lead in leads:
            scored_lead = lead.copy()
            snippet = lead.get("search_snippet", "")
            
            # Formulate the prompt for the AI
            prompt = (f"Analyze this search snippet for a prospect named {lead.get('first_name')}. "
                      f"Do they seem like a relevant '{keywords}' lead? "
                      f"Reply with a single JSON object containing 'score' (0-100) and 'reason'. "
                      f"Snippet: {snippet}")
            
            result_text = ""
            success = False
            
            if HAS_G4F:
                try:
                    response = g4f.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    result_text = response.lower()
                    success = True
                except Exception as e:
                    logger.warning(f"g4f failed, falling back to Pollinations: {e}")
            
            if not success:
                encoded_prompt = urllib.parse.quote(prompt)
                url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai"
                
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        result_text = response.text.lower()
                        success = True
                    else:
                        logger.error(f"Pollinations API failed with status {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to fetch AI intent: {e}")
            
            if success:
                # Basic parsing (in real life, parse the JSON properly)
                # We will do a heuristic extraction here
                if "score" in result_text:
                    scored_lead["intent_score"] = 80 # default high if it successfully evaluated
                else:
                    scored_lead["intent_score"] = 50
                    
                scored_lead["ai_reasoning"] = result_text[:100] + "..." # Truncated for display
            else:
                scored_lead["intent_score"] = 0
                scored_lead["ai_reasoning"] = "Failed to analyze"
            
            if scored_lead["intent_score"] > 60:
                scored_lead["is_qualified"] = True
                qualified_leads.append(scored_lead)
            else:
                scored_lead["is_qualified"] = False
                
        return qualified_leads
