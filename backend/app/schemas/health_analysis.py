from datetime import datetime
from pydantic import BaseModel


class HealthAnalysisResponse(BaseModel):
    person_id: str
    analyzed_at: datetime
    data_sufficient: bool
    abnormal_indicators: list[str]
    long_term_symptoms: list[str]
    potential_risks: list[str]
    follow_up_items: list[str]
    recommendations: list[str]
    disclaimer: str
