from pydantic import BaseModel
from typing import List, Optional, Dict

class BatchInput(BaseModel):
    uri: str
    doc_id: Optional[str] = None

class BatchManifest(BaseModel):
    batch_id: str
    lane: str  # "text" | "audio" | "curator"
    language: str
    dialect: str
    inputs: List[BatchInput]
    outputs: Dict[str, str] = {}
    metrics: Dict[str, float] = {}
    status: str = "created"
