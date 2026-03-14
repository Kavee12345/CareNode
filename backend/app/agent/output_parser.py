"""
Extract metadata (escalation level, etc.) from natural-language responses.
No JSON parsing needed — the LLM responds in plain text.
"""
from typing import List


EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "stroke", "can't breathe", "cannot breathe",
    "difficulty breathing", "shortness of breath", "unconscious", "severe bleeding",
    "anaphylaxis", "allergic reaction severe", "call 911", "emergency room",
    "worst headache", "sudden vision loss", "facial droop", "seek emergency care",
]

URGENT_KEYWORDS = [
    "high fever", "fever 103", "fever 104", "fever 105",
    "blood clot", "dvt", "pulmonary embolism",
    "severe pain", "uncontrolled", "worsening rapidly",
    "see a doctor soon", "see your doctor",
]

MILD_KEYWORDS = [
    "monitor", "keep an eye on", "routine check", "follow up with your doctor",
    "schedule an appointment", "worth mentioning",
]


def extract_escalation(text: str) -> str:
    """Detect escalation level from keywords in the text."""
    text_lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            return "emergency"
    for kw in URGENT_KEYWORDS:
        if kw in text_lower:
            return "urgent"
    for kw in MILD_KEYWORDS:
        if kw in text_lower:
            return "mild"
    return "none"


def extract_follow_ups(text: str) -> List[str]:
    """Extract follow-up questions from text after --- separator."""
    parts = text.split("\n---\n")
    if len(parts) < 2:
        return []
    follow_ups = []
    for line in parts[1].strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            follow_ups.append(line[2:].strip())
        elif line.startswith("* "):
            follow_ups.append(line[2:].strip())
    return follow_ups
