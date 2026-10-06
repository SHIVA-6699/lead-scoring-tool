import re

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "LeadScoringTool/1.0 (+https://github.com/SHIVA-6699/lead-scoring-tool)"
REQUEST_TIMEOUT = 8.0

TOOL_SIGNATURES = {
    "hubspot": "HubSpot",
    "intercom": "Intercom",
    "drift.com": "Drift",
    "salesforce": "Salesforce",
    "marketo": "Marketo",
    "segment.com": "Segment",
    "mixpanel": "Mixpanel",
    "js.stripe.com": "Stripe",
    "intercomcdn": "Intercom",
}

CAREERS_WORDS = ("career", "jobs", "hiring", "join us", "join our team")
PRICING_WORDS = ("pricing", "plans")
BLOG_WORDS = ("blog", "news", "insights")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def normalize_domain(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/")[0]
    return value.removeprefix("www.")


async def fetch_signals(domain: str) -> dict:
    """Fetch a company's homepage and pull out signals useful for scoring a lead."""
    url = f"https://{domain}"
    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=REQUEST_TIMEOUT, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError:
        return {"reachable": False, "company_name": domain, "html": "", "final_url": url}

    return {
        "reachable": True,
        "company_name": _guess_company_name(response.text, domain),
        "html": response.text,
        "final_url": str(response.url),
    }


def extract_signals(domain: str, html: str, final_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    links = [a.get("href", "").lower() for a in soup.find_all("a", href=True)]

    return {
        "has_careers_page": any(word in " ".join(links) or word in text for word in CAREERS_WORDS),
        "has_pricing_page": any(word in " ".join(links) for word in PRICING_WORDS),
        "has_blog": any(word in " ".join(links) for word in BLOG_WORDS),
        "has_linkedin": any("linkedin.com/company" in link for link in links),
        "contact_email": _first_email(text),
        "tools_detected": _detect_tools(html, domain),
        "uses_https": final_url.startswith("https://"),
        "mobile_friendly": soup.find("meta", attrs={"name": "viewport"}) is not None,
        "employee_count_hint": _guess_employee_count(text),
    }


def _guess_company_name(html: str, domain: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    site_name_tag = soup.find("meta", attrs={"property": "og:site_name"})
    if site_name_tag and site_name_tag.get("content"):
        return site_name_tag["content"].strip()

    root_name = domain.split(".")[0]
    return root_name.replace("-", " ").title()


def _first_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _detect_tools(html: str, domain: str) -> list[str]:
    lowered = html.lower()
    found = {name for key, name in TOOL_SIGNATURES.items() if key in lowered and key not in domain}
    return sorted(found)


def _guess_employee_count(text: str) -> int | None:
    match = re.search(r"(\d{1,5})\+?\s+employees", text)
    return int(match.group(1)) if match else None
