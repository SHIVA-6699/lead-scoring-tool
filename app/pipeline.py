import asyncio
from datetime import UTC, datetime

from app import db
from app.scorer import score_lead
from app.scraper import extract_signals, fetch_signals, normalize_domain

CACHE_HOURS = 24
MAX_CONCURRENT_SCRAPES = 5


async def analyze_domains(raw_domains: list[str]) -> list[dict]:
    domains = _dedupe(normalize_domain(d) for d in raw_domains if d.strip())
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

    results = await asyncio.gather(*(_analyze_one(domain, semaphore) for domain in domains))
    return sorted(results, key=lambda lead: lead["score"], reverse=True)


async def _analyze_one(domain: str, semaphore: asyncio.Semaphore) -> dict:
    cached = db.get_cached_lead(domain, CACHE_HOURS)
    if cached is not None:
        return {**cached, "cached": True}

    async with semaphore:
        fetched = await fetch_signals(domain)

    if not fetched["reachable"]:
        result = {
            "domain": domain,
            "company_name": domain,
            "score": 0,
            "bucket": "cold",
            "reasons": ["Could not reach the website"],
            "signals": {},
            "reachable": False,
            "scraped_at": datetime.now(UTC).isoformat(),
            "cached": False,
        }
        db.save_lead(result)
        return result

    signals = extract_signals(domain, fetched["html"], fetched["final_url"])
    score, bucket, reasons = score_lead(signals)

    result = {
        "domain": domain,
        "company_name": fetched["company_name"],
        "score": score,
        "bucket": bucket,
        "reasons": reasons,
        "signals": signals,
        "reachable": True,
        "scraped_at": datetime.now(UTC).isoformat(),
        "cached": False,
    }
    db.save_lead(result)
    return result


def _dedupe(domains) -> list[str]:
    seen = []
    for domain in domains:
        if domain and domain not in seen:
            seen.append(domain)
    return seen
