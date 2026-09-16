from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    log: str


class SimilarIncident(BaseModel):
    id: int
    log: str
    category: str
    severity: str
    root_cause: str
    resolution: list[str]
    similarity: float


class AnalyzeResponse(BaseModel):
    incident_id: int
    category: str
    severity: str
    root_cause: str
    recommended_actions: list[str]
    confidence: float
    similar_incidents: list[SimilarIncident]


class IncidentSummary(BaseModel):
    id: int
    timestamp: str
    category: str
    severity: str
    root_cause: str

    class Config:
        from_attributes = True


class IncidentDetail(BaseModel):
    id: int
    timestamp: str
    raw_log: str
    cleaned_log: str
    category: str
    severity: str
    root_cause: str
    recommended_actions: list[str]
    confidence: float

    class Config:
        from_attributes = True