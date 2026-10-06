import csv
import io

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db
from app.pipeline import analyze_domains

app = FastAPI(title="Lead Scoring Tool")


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


class AnalyzeRequest(BaseModel):
    domains: list[str] = Field(min_length=1, max_length=50)


@app.post("/api/analyze")
async def analyze(data: AnalyzeRequest) -> list[dict]:
    return await analyze_domains(data.domains)


@app.get("/api/leads")
def leads() -> list[dict]:
    return db.list_leads()


@app.get("/api/export")
def export_csv() -> StreamingResponse:
    rows = db.list_leads()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["company_name", "domain", "score", "bucket", "top_reason", "scraped_at"])
    for row in rows:
        top_reason = row["reasons"][0] if row["reasons"] else ""
        writer.writerow([row["company_name"], row["domain"], row["score"], row["bucket"], top_reason, row["scraped_at"]])

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
