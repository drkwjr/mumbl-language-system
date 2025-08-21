from pydantic import BaseModel, Field
from typing import Optional

class SegmentScore(BaseModel):
    clarity: float = Field(ge=0, le=100)
    alignment: float = Field(ge=0, le=100)
    diarization: float = Field(ge=0, le=100)
    transcript_accuracy: float = Field(ge=0, le=100)
    validity: float = Field(ge=0, le=100)  # language, register
    shape: float = Field(ge=0, le=100)     # length and structure
    total: float = Field(ge=0, le=100)
    eligible_learner: bool
    eligible_training: bool
    notes: Optional[str] = None
