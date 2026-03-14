import json
import re
from app.schemas.chat import MedicalResponse


# Emergency keywords that override LLM escalation level
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "stroke", "can't breathe", "cannot breathe",
    "difficulty breathing", "shortness of breath", "unconscious", "severe bleeding",
    "anaphylaxis", "allergic reaction severe", "call 911", "emergency room",
    "worst headache", "sudden vision loss", "facial droop",
]

URGENT_KEYWORDS = [
    "high fever", "fever 103", "fever 104", "fever 105",
    "blood clot", "dvt", "pulmonary embolism",
    "severe pain", "uncontrolled", "worsening rapidly",
]


def parse_medical_response(raw_text: str, user_message: str = "") -> MedicalResponse:
    """
    Parse the LLM's JSON response into a validated MedicalResponse.
    Falls back gracefully if the JSON is malformed.
    Escalation level is the MAX of LLM's value and keyword-detected value.
    """
    parsed = _try_parse_json(raw_text)

    if parsed is None:
        # Fallback: treat the raw text as the answer
        parsed = {
            "answer": raw_text,
            "escalation_level": "none",
            "confidence": 0.5,
            "recommendations": ["Please consult a healthcare professional for personalized advice."],
            "disclaimer": "This information is for educational purposes only. Always consult a qualified healthcare professional.",
            "sources": [],
        }

    # Keyword-based escalation override (safety net)
    keyword_escalation = _detect_escalation_from_keywords(user_message + " " + parsed.get("answer", ""))
    llm_escalation = parsed.get("escalation_level", "none")
    parsed["escalation_level"] = _max_escalation(llm_escalation, keyword_escalation)

    # Ensure disclaimer is always present
    if not parsed.get("disclaimer"):
        parsed["disclaimer"] = (
            "This information is for educational purposes only and does not constitute medical advice. "
            "Always consult a qualified healthcare professional for diagnosis and treatment."
        )

    return MedicalResponse(**parsed)


def _try_parse_json(text: str) -> dict | None:
    """Try to extract and parse JSON from the response text."""
    # Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Extract JSON block from markdown code fence
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Find the largest {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _detect_escalation_from_keywords(text: str) -> str:
    text_lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            return "emergency"
    for kw in URGENT_KEYWORDS:
        if kw in text_lower:
            return "urgent"
    return "none"


ESCALATION_RANK = {"none": 0, "mild": 1, "urgent": 2, "emergency": 3}


def _max_escalation(a: str, b: str) -> str:
    rank_a = ESCALATION_RANK.get(a, 0)
    rank_b = ESCALATION_RANK.get(b, 0)
    return a if rank_a >= rank_b else b
