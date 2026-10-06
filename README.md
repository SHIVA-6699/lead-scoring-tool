# Lead Scoring Tool

A tool that takes a list of company websites, scrapes each one, and scores it as a sales lead with a plain English reason for the score. Built for the Caprae Capital AI-readiness challenge, as an improvement on the lead generation idea behind SaaSquatch.

## Why lead scoring

A scraper that just dumps company data is only half useful. A sales team still has to read through every row and decide who to call first. This tool does that ranking automatically and explains the reasoning, so a rep can open the list and immediately see which leads are worth calling today and why.

## How scoring works

Each company's homepage is scraped once and checked for signals that matter for a sales lead:

- Has a careers page (company is hiring, so it is growing)
- Has a pricing page (product is already monetized)
- A contact email was found (easy to reach)
- Has a LinkedIn company page
- Publishes a blog (active marketing team)
- Uses HTTPS and is mobile friendly (modern web presence)
- Uses tools like HubSpot, Intercom, Salesforce, Marketo, Segment or Mixpanel (has budget for sales and marketing tools)
- Employee count mentioned on the page, if it falls in a reasonable outreach range

Each signal adds points, capped at 100. A lead scores 70+ as hot, 40-69 as warm, below 40 as cold. The reasons are shown next to the score, so the ranking is never a black box.

This is rule based rather than machine learning. With a 5 hour time limit, a rule based score that a sales person can trust and verify is more useful than a model that can't explain itself.

## Architecture

- **Backend:** FastAPI (Python), serving both the JSON API and the static frontend from one process.
- **Scraping:** httpx for async HTTP requests, BeautifulSoup for parsing. Domains are scraped concurrently with a limit of 5 at a time, so a batch of leads finishes in seconds instead of scraping one by one.
- **Storage:** SQLite. One `leads` table holds the latest scraped result per domain. SQLite needs no setup, which fits a tool this size, and the schema is one table so there is nothing to migrate.
- **Caching:** a domain that was scraped in the last 24 hours is served from the database instead of being scraped again. This avoids hitting the same site repeatedly and makes repeat lookups return instantly, which matters once a sales team is checking the same leads over multiple days.
- **Frontend:** a single HTML page with Tailwind (CDN) and plain JavaScript, no build step. Paste a list of domains, see them scored and ranked, export to CSV.

### Hosting and deployment

For this submission the app runs as a single process (`uvicorn app.main:app`), which is enough to demo and review locally.

For a production deployment at small to medium scale, I would keep the same single container and deploy it to a platform like Render or Railway: one Dockerfile, one service, SQLite replaced with a managed Postgres instance since the container's local disk is not persistent on most platforms. This keeps hosting cost and complexity low, which fits a tool a small sales team would use.

At a larger scale, where many users are scraping large batches concurrently, I would split the app: the frontend as a static site on Vercel or Netlify, and the backend as a serverless function (AWS Lambda behind API Gateway, using Mangum) so scraping load scales independently of the UI. The scraping queue itself would move to a background worker (e.g. SQS plus a worker service) instead of running inside the request, since scraping many domains in one HTTP request does not scale well past a request timeout.

## Ethical scraping

Only the public homepage of each domain is fetched, once per 24 hours. Requests use a descriptive user agent and a timeout, and no login, captcha bypass, or crawling beyond the homepage is attempted.

## Tech stack

- Python, FastAPI, httpx, BeautifulSoup4, SQLite
- HTML, Tailwind CSS (CDN), vanilla JavaScript
- pytest for the scoring logic

## Running it

Requirements: Python 3.12+

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS or Linux use `source .venv/bin/activate` instead.

Open http://localhost:8000, click "Try demo leads" to fill in a sample list, then click "Analyze leads".

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover the scoring logic directly, since that is the core business decision the tool makes.

## Project structure

```
app/
  main.py        FastAPI app and routes
  pipeline.py     ties scraping, scoring and caching together
  scraper.py      fetches a homepage and extracts signals
  scorer.py       turns signals into a score and reasons
  db.py           SQLite storage and caching
  static/         frontend (index.html, app.js)
tests/
  test_scorer.py  unit tests for the scoring logic
```

## What I would add with more time

- Bulk upload from a CSV of company names, resolving each to a domain automatically
- A browser extension or API endpoint so the score can be checked for a single lead while a rep is live on a call
- Enrichment from a second source (e.g. an email verification API) to double check the contact email found on the homepage
- A saved list per user instead of one shared table, once authentication is in scope
