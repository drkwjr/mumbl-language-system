from typing import Dict, List, Optional

from pydantic import BaseModel


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
