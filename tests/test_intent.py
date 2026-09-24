"""Tests for the OpenAI-compatible intent client (no network, no real key)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.intent import IntentAnalyzer  # noqa: E402


def _resp(payload, status=200):
    class R:
        status_code = status
        text = "err"

        def json(self):
            return payload

    return R()


def _ok_response(score=85, reason="Strong fit"):
    return _resp({"choices": [{"message": {"content": f'{{"score": {score}, "reason": "{reason}"}}'}}]})


def test_parse_score_plain_and_fenced():
    assert IntentAnalyzer._parse_score('{"score": 90, "reason": "x"}') == {"score": 90, "reason": "x"}
    fenced = '```json\n{"score": 42, "reason": "y"}\n```'
    assert IntentAnalyzer._parse_score(fenced)["score"] == 42
    assert IntentAnalyzer._parse_score("no json here") is None
    assert IntentAnalyzer._parse_score('{"score": 999}')["score"] == 100  # clamped


def test_score_intent_with_mocked_llm():
    analyzer = IntentAnalyzer(openai_api_key="dummy")
    leads = [{"id": "1", "first_name": "Asha", "last_name": "K",
              "title": "CTO", "company": "Acme", "search_snippet": "CTO at Acme"}]
    with patch("core.intent.requests.post", return_value=_ok_response(85, "Strong fit")):
        out = analyzer.score_intent(leads, keywords="SaaS")
    assert len(out) == 1
    assert out[0]["intent_score"] == 85
    assert out[0]["is_qualified"] is True
    assert out[0]["ai_reasoning"] == "Strong fit"


def test_low_score_not_qualified():
    analyzer = IntentAnalyzer(openai_api_key="dummy")
    leads = [{"id": "1", "first_name": "B", "title": "Intern", "company": "X", "search_snippet": "y"}]
    with patch("core.intent.requests.post", return_value=_ok_response(20, "Weak")):
        out = analyzer.score_intent(leads, keywords="SaaS")
    assert out == []


def test_no_key_degrades_gracefully():
    analyzer = IntentAnalyzer(openai_api_key=None)
    # ensure env doesn't leak a key into this test
    analyzer.api_key = None
    leads = [{"id": "1", "first_name": "A", "title": "CTO", "company": "Acme", "search_snippet": "z"}]
    out = analyzer.score_intent(leads, keywords="SaaS")
    assert out == []
    # the scored lead is marked unqualified, not fabricated
    # (score_intent returns only qualified; absence here proves no fake 80s)


def test_api_error_degrades_gracefully():
    analyzer = IntentAnalyzer(openai_api_key="dummy-bad-key")
    leads = [{"id": "1", "first_name": "A", "title": "CTO", "company": "Acme", "search_snippet": "z"}]
    with patch("core.intent.requests.post", return_value=_resp({}, status=401)):
        out = analyzer.score_intent(leads, keywords="SaaS")
    assert out == []  # 401 -> no fake qualification


def test_uses_bearer_auth_and_base_url():
    analyzer = IntentAnalyzer(openai_api_key="k123", base_url="https://example.com/v1", model="m")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _ok_response()

    with patch("core.intent.requests.post", side_effect=fake_post):
        analyzer.score_intent([{"id": "1", "first_name": "A", "title": "T",
                                "company": "C", "search_snippet": "s"}], keywords="k")
    assert captured["url"] == "https://example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer k123"
    assert captured["json"]["model"] == "m"
