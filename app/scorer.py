SCORE_RULES = [
    ("has_careers_page", 15, "Actively hiring, which usually means the company is growing"),
    ("has_pricing_page", 15, "Has a public pricing page, so the product is already monetized"),
    ("contact_email", 15, "A contact email was found, so outreach is easy"),
    ("has_linkedin", 10, "Has an active LinkedIn company page"),
    ("has_blog", 10, "Publishes a blog, which signals an active marketing team"),
    ("uses_https", 5, "Site uses HTTPS, a sign of a maintained web presence"),
    ("mobile_friendly", 5, "Site is mobile-friendly, a sign of a modern tech setup"),
]

TOOL_POINTS_PER_TOOL = 5
TOOL_POINTS_CAP = 15

EMPLOYEE_SWEET_SPOT = (10, 500)
EMPLOYEE_SWEET_SPOT_POINTS = 10

HOT_THRESHOLD = 70
WARM_THRESHOLD = 40


def score_lead(signals: dict) -> tuple[int, str, list[str]]:
    """Turn raw scraped signals into a 0-100 score with plain-English reasons."""
    score = 0
    reasons = []

    for key, points, reason in SCORE_RULES:
        if signals.get(key):
            score += points
            reasons.append(reason)

    tools = signals.get("tools_detected") or []
    if tools:
        tool_points = min(len(tools) * TOOL_POINTS_PER_TOOL, TOOL_POINTS_CAP)
        score += tool_points
        reasons.append(f"Uses {', '.join(tools)}, which shows budget for sales/marketing tools")

    employee_count = signals.get("employee_count_hint")
    if employee_count and EMPLOYEE_SWEET_SPOT[0] <= employee_count <= EMPLOYEE_SWEET_SPOT[1]:
        score += EMPLOYEE_SWEET_SPOT_POINTS
        reasons.append(f"Around {employee_count} employees, a good size for outreach")

    score = min(score, 100)
    bucket = "hot" if score >= HOT_THRESHOLD else "warm" if score >= WARM_THRESHOLD else "cold"
    return score, bucket, reasons
