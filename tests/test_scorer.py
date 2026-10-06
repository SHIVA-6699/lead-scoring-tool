from app.scorer import SCORE_RULES, score_lead


def test_strong_signals_score_as_hot():
    signals = {
        "has_careers_page": True,
        "has_pricing_page": True,
        "contact_email": "sales@example.com",
        "has_linkedin": True,
        "has_blog": True,
        "uses_https": True,
        "mobile_friendly": True,
        "tools_detected": ["HubSpot", "Intercom"],
        "employee_count_hint": 50,
    }

    score, bucket, reasons = score_lead(signals)

    assert score == 95
    assert bucket == "hot"
    assert len(reasons) > 0


def test_no_signals_score_as_cold():
    score, bucket, reasons = score_lead({})

    assert score == 0
    assert bucket == "cold"
    assert reasons == []


def test_tool_points_are_capped():
    signals = {"tools_detected": ["HubSpot", "Intercom", "Salesforce", "Marketo", "Segment", "Mixpanel"]}

    score, _, _ = score_lead(signals)

    assert score == 15


def test_employee_count_outside_sweet_spot_gets_no_bonus():
    signals = {"employee_count_hint": 50000}

    score, _, _ = score_lead(signals)

    assert score == 0


def test_score_never_exceeds_100():
    signals = {key: True for key, _, _ in SCORE_RULES}
    signals["tools_detected"] = ["HubSpot", "Intercom", "Salesforce", "Marketo"]
    signals["employee_count_hint"] = 100

    score, _, _ = score_lead(signals)

    assert score == 100
