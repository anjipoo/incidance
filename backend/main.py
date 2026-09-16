import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from backend.database import init_db, get_db
from backend.models import Incident
from backend.schemas import AnalyzeRequest, AnalyzeResponse, IncidentSummary, IncidentDetail
from backend.services.log_parser import clean_log
from backend.services.retriever import build_index
from backend.services.resolver import analyze_incident

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incident_resolver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: create DB tables and build the FAISS index
    # so every request onward can search immediately without rebuilding.
    logger.info("Initializing database...")
    init_db()
    logger.info("Building FAISS index...")
    build_index()
    logger.info("Startup complete.")
    yield


app = FastAPI(title="AI Incident Resolver", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/incidents/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    if not request.log or not request.log.strip():
        raise HTTPException(status_code=400, detail="Log input cannot be empty")

    try:
        cleaned = clean_log(request.log)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = analyze_incident(cleaned)
    except RuntimeError as e:
        # Covers: missing/invalid API key, Gemini unavailable, malformed response.
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=502, detail=f"Incident analysis failed: {e}")

    incident = Incident(
        raw_log=request.log,
        cleaned_log=cleaned,
        category=result["category"],
        severity=result["severity"],
        root_cause=result["root_cause"],
        recommended_actions=json.dumps(result["recommended_actions"]),
        confidence=result["confidence"],
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return AnalyzeResponse(
        incident_id=incident.id,
        category=result["category"],
        severity=result["severity"],
        root_cause=result["root_cause"],
        recommended_actions=result["recommended_actions"],
        confidence=result["confidence"],
        similar_incidents=result["similar_incidents"],
    )


@app.post("/incidents", response_model=IncidentDetail)
def create_incident(request: AnalyzeRequest, db: Session = Depends(get_db)):
    # Thin alias endpoint per the spec — same behavior as /incidents/analyze
    # but returns the stored record shape instead of the full analysis shape.
    analyze_result = analyze(request, db)
    db_incident = db.query(Incident).filter(Incident.id == analyze_result.incident_id).first()
    return _to_detail(db_incident)


@app.get("/incidents", response_model=list[IncidentSummary])
def list_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.timestamp.desc()).all()
    return [
        IncidentSummary(
            id=i.id,
            timestamp=i.timestamp.isoformat(),
            category=i.category,
            severity=i.severity,
            root_cause=i.root_cause,
        )
        for i in incidents
    ]


@app.get("/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return _to_detail(incident)


def _to_detail(incident: Incident) -> IncidentDetail:
    return IncidentDetail(
        id=incident.id,
        timestamp=incident.timestamp.isoformat(),
        raw_log=incident.raw_log,
        cleaned_log=incident.cleaned_log,
        category=incident.category,
        severity=incident.severity,
        root_cause=incident.root_cause,
        recommended_actions=json.loads(incident.recommended_actions),
        confidence=incident.confidence,
    )