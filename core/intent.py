"""
Intent scoring via a real OpenAI-compatible chat-completions API.

Configuration (env vars, also accepted as constructor args):
    OPENAI_API_KEY   - required for real scoring; without it every lead is
                       marked "LLM unavailable" and the pipeline continues
                       (no crash, no fake scores).
    OPENAI_BASE_URL  - default https://api.openai.com/v1
                       (any OpenAI-compatible endpoint works)
    OPENAI_MODEL     - default gpt-4o-mini

The old g4f (unofficial reverse-engineered client) and Pollinations.ai
fallbacks have been removed: they were fragile, unauthenticated, and their
"scores" were fabricated heuristics (score=80 when the word "score" appeared
in the reply).
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
QUALIFY_THRESHOLD = 60


class IntentAnalyzer:
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL

    # -- LLM plumbing ------------------------------------------------------

    def _chat(self, prompt: str, timeout: int = 30) -> str:
        """One chat-completions call. Raises RuntimeError on any failure."""
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You score B2B sales leads. Reply with a single JSON object: "
                        '{"score": <0-100 integer>, "reason": "<one sentence>"}.'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"LLM request failed: {e}")
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API returned {resp.status_code}: {resp.text[:200]}")
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(f"Unexpected LLM response shape: {e}")
        return content

    @staticmethod
    def _parse_score(text: str) -> Optional[Dict[str, Any]]:
        """Extract {"score", "reason"} from model output, tolerating fences/extra text."""
        if not text:
            return None
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        candidate = m.group(1) if m else text
        try:
            data = json.loads(candidate)
        except ValueError:
            m2 = re.search(r"\{[^{}]*\"score\"[^{}]*\}", text, re.DOTALL)
            if not m2:
                return None
            try:
                data = json.loads(m2.group(0))
            except ValueError:
                return None
        try:
            score = int(data["score"])
        except (KeyError, TypeError, ValueError):
            return None
        score = max(0, min(100, score))
        return {"score": score, "reason": str(data.get("reason", ""))[:200]}

    # -- pipeline step -------------------------------------------------------

    def score_intent(self, leads: List[Dict[str, Any]], keywords: str) -> List[Dict[str, Any]]:
        """Score each lead's buying intent. Degrades gracefully without a working key."""
        logger.info("Analyzing intent and buying signals...")

        qualified_leads = []
        for lead in leads:
            scored_lead = lead.copy()
            snippet = lead.get("search_snippet", "") or ""
            prompt = (
                f"Prospect: {lead.get('first_name', '')} {lead.get('last_name', '')} "
                f"({lead.get('title', '')} at {lead.get('company', '')}). "
                f"Target keywords: '{keywords}'. Bio/snippet: {snippet[:800]} "
                "How relevant is this prospect as a lead? "
                'Reply with a single JSON object: {"score": 0-100, "reason": "..."}.'
            )
            try:
                raw = self._chat(prompt)
                parsed = self._parse_score(raw)
                if parsed is None:
                    raise RuntimeError(f"Could not parse LLM output: {raw[:120]!r}")
                scored_lead["intent_score"] = parsed["score"]
                scored_lead["ai_reasoning"] = parsed["reason"]
                scored_lead["is_qualified"] = parsed["score"] >= QUALIFY_THRESHOLD
            except RuntimeError as e:
                # Honest degradation: no fake score, pipeline continues.
                logger.warning(f"Intent scoring skipped for lead {lead.get('id')}: {e}")
                scored_lead["intent_score"] = 0
                scored_lead["ai_reasoning"] = f"LLM unavailable: {e}"
                scored_lead["is_qualified"] = False

            if scored_lead["is_qualified"]:
                qualified_leads.append(scored_lead)

        return qualified_leads
