from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict

class SourceRef(BaseModel):
    doc_id: str
    start: int
    end: int

class Labels(BaseModel):
    is_dialogue: bool
    topic: Optional[str] = None
    register_type: Optional[str] = None
    code_switch_spans: List[Tuple[int, int]] = []

class TextSegment(BaseModel):
    text: str
    lang: str
    labels: Labels
    source_ref: SourceRef

class AudioSegment(BaseModel):
    audio_file: str
    start: float
    end: float
    speaker_id: Optional[str] = None
    transcript_text: Optional[str] = None
    lang: Optional[str] = None
    dialect_probs: Optional[Dict[str, float]] = None
    alignment_confidence: Optional[float] = None
    diarization_confidence: Optional[float] = None
