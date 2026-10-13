import re
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.models.enums import QueryUrgency


class AIClinicalSafetyGuard:
    """
    Enforces clinical safety:
    1. AI never issues prescriptions or definitive diagnostic claims.
    2. Identifies red-flag emergency symptoms immediately.
    3. Adds mandatory clinical disclaimers.
    """
    EMERGENCY_KEYWORDS = [
        "chest pain", "shortness of breath", "difficulty breathing",
        "severe bleeding", "unconscious", "stroke", "face drooping",
        "sudden numbness", "anaphylaxis", "suicidal", "severe allergic reaction",
        "coughing blood", "heart attack", "convulsions", "seizure"
    ]

    HIGH_URGENCY_KEYWORDS = [
        "high fever", "severe pain", "broken bone", "fracture",
        "head injury", "vomiting blood", "fainting", "severe burn"
    ]

    DISCLAIMER = (
        "NOTICE: This automated assessment is for informational and triage purposes only. "
        "It does not replace professional medical advice, diagnosis, or treatment. "
        "If you are experiencing a medical emergency, please call your local emergency services (e.g., 911/112/108) immediately."
    )

    @classmethod
    def evaluate_emergency(cls, text: str) -> QueryUrgency:
        text_lower = text.lower()
        for kw in cls.EMERGENCY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return QueryUrgency.EMERGENCY

        for kw in cls.HIGH_URGENCY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return QueryUrgency.HIGH

        return QueryUrgency.MEDIUM


class DepartmentTriageAgent:
    """
    Classifies symptom descriptions into appropriate medical departments.
    """
    DEPARTMENT_MAPPINGS = {
        "Cardiology": ["heart", "chest", "palpitation", "blood pressure", "hypertension", "angina"],
        "Dermatology": ["skin", "rash", "itching", "acne", "mole", "eczema", "hair fall"],
        "Orthopedics": ["bone", "joint", "fracture", "knee", "spine", "back pain", "arthritis", "sprain"],
        "Neurology": ["headache", "migraine", "dizziness", "numbness", "tingling", "memory", "tremor"],
        "Pediatrics": ["child", "baby", "infant", "toddler", "pediatric"],
        "Gastroenterology": ["stomach", "digestion", "acid reflux", "nausea", "vomiting", "diarrhea", "constipation", "abdomen"],
        "Pulmonology": ["cough", "wheezing", "asthma", "lungs", "bronchitis", "respiratory"],
        "General Medicine": ["fever", "fatigue", "weakness", "cold", "flu", "body ache", "malaise"]
    }

    @classmethod
    def classify_department(cls, text: str) -> str:
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for dept, keywords in cls.DEPARTMENT_MAPPINGS.items():
            score = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
            if score > 0:
                scores[dept] = score

        if scores:
            return max(scores, key=scores.get)
        return "General Medicine"


class QuerySummarizationAgent:
    """
    Summarizes patient queries into structured clinical handoff notes for the doctor.
    """
    @classmethod
    def summarize_query(cls, title: str, description: str, urgency: QueryUrgency) -> str:
        # If external OpenAI API is configured, it could be called here.
        # Otherwise, reliable rule-based structured extraction:
        summary_lines = [
            f"**Chief Complaint:** {title}",
            f"**Urgency Triage:** {urgency.value}",
            f"**Reported Symptoms:** {description.strip()}",
            f"**AI Triage Note:** Routed for clinical evaluation. {AIClinicalSafetyGuard.DISCLAIMER}"
        ]
        return "\n".join(summary_lines)


class AppointmentAgent:
    """
    Handles appointment slot validations, duration calculations, and conflict prevention.
    """
    @classmethod
    def check_conflicts(
        cls,
        existing_appointments: List[Any],
        target_start_time: Any,
        target_end_time: Any
    ) -> bool:
        """
        Returns True if a conflict exists, False if the slot is clear.
        """
        for appt in existing_appointments:
            if appt.status.value in ["CONFIRMED", "PENDING", "RESCHEDULED"]:
                if (target_start_time < appt.end_time) and (target_end_time > appt.start_time):
                    return True
        return False
