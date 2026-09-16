from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Incident(Base):
    # Stores each analyzed incident and the structured result Gemini returned.
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_log = Column(Text, nullable=False)
    cleaned_log = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    root_cause = Column(Text, nullable=False)
    # Stored as a JSON-encoded string since SQLite has no native array type.
    recommended_actions = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)