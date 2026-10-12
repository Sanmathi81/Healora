from app.ai.agents import AIClinicalSafetyGuard, DepartmentTriageAgent, QuerySummarizationAgent
from app.models.enums import QueryUrgency


def test_ai_safety_emergency_detection():
    # Emergency keyword: chest pain
    urgency = AIClinicalSafetyGuard.evaluate_emergency("I have sudden acute chest pain radiating down my left arm")
    assert urgency == QueryUrgency.EMERGENCY

    # Emergency keyword: shortness of breath
    urgency2 = AIClinicalSafetyGuard.evaluate_emergency("Severe shortness of breath since 20 minutes ago")
    assert urgency2 == QueryUrgency.EMERGENCY

    # High urgency keyword: high fever
    urgency3 = AIClinicalSafetyGuard.evaluate_emergency("Child has high fever for 2 days")
    assert urgency3 == QueryUrgency.HIGH

    # Routine / Medium urgency
    urgency4 = AIClinicalSafetyGuard.evaluate_emergency("I need a routine refill for my vitamin supplements")
    assert urgency4 == QueryUrgency.MEDIUM


def test_department_triage_routing():
    assert DepartmentTriageAgent.classify_department("Severe chest flutter and irregular heart palpitations") == "Cardiology"
    assert DepartmentTriageAgent.classify_department("Red itchy rash on forehead and dry skin") == "Dermatology"
    assert DepartmentTriageAgent.classify_department("Sprained right knee and swelling in spine joint") == "Orthopedics"
    assert DepartmentTriageAgent.classify_department("Constant migraine and dizziness") == "Neurology"
    assert DepartmentTriageAgent.classify_department("Toddler fever and pediatric cough") == "Pediatrics"
    assert DepartmentTriageAgent.classify_department("Acid reflux, nausea, and severe stomach pain") == "Gastroenterology"
    assert DepartmentTriageAgent.classify_department("Persistent wheezing, asthma flare up, lung tightness") == "Pulmonology"
    assert DepartmentTriageAgent.classify_department("General fatigue and malaise") == "General Medicine"


def test_query_summarization_includes_disclaimer():
    summary = QuerySummarizationAgent.summarize_query(
        title="Sprained ankle",
        description="Twisted ankle while stepping down stairs.",
        urgency=QueryUrgency.MEDIUM
    )
    assert "**Chief Complaint:** Sprained ankle" in summary
    assert "NOTICE: This automated assessment is for informational and triage purposes only." in summary
