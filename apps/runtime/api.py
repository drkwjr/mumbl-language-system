from typing import Dict, List, Optional

from fastapi import FastAPI
from mumbl_orchestration.flows_audio import audio_lane_flow
from mumbl_orchestration.flows_curator import curator_flow
from mumbl_orchestration.flows_text import text_lane_flow
from pydantic import BaseModel

# Import TTS training flow
try:
    from mumbl_orchestration.flows_tts import tts_training_flow
except ImportError:
    # Fallback if flow not available
    def tts_training_flow(manifest: dict) -> dict:
        return {"status": "not_implemented", "message": "TTS training flow not available"}


app = FastAPI(title="Mumbl Runtime Admin API", version="0.1.0")


class BatchInput(BaseModel):
    uri: str
    doc_id: Optional[str] = None


class FlowRequest(BaseModel):
    batch_id: str
    lane: str
    language: str
    dialect: str
    inputs: List[BatchInput]


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/flows/text")
def launch_text(req: FlowRequest):
    man = {
        "batch_id": req.batch_id,
        "lane": "text",
        "language": req.language,
        "dialect": req.dialect,
        "inputs": [i.dict() for i in req.inputs],
    }
    return text_lane_flow(man)


@app.post("/flows/audio")
def launch_audio(req: FlowRequest):
    man = {
        "batch_id": req.batch_id,
        "lane": "audio",
        "language": req.language,
        "dialect": req.dialect,
        "inputs": [i.dict() for i in req.inputs],
    }
    return audio_lane_flow(man)


@app.post("/flows/curator")
def launch_curator(req: FlowRequest):
    man = {
        "batch_id": req.batch_id,
        "lane": "curator",
        "language": req.language,
        "dialect": req.dialect,
        "inputs": [i.dict() for i in req.inputs],
    }
    return curator_flow(man)


@app.post("/flows/tts-training")
def launch_tts_training(req: FlowRequest):
    man = {
        "batch_id": req.batch_id,
        "lane": "tts-training",
        "language": req.language,
        "dialect": req.dialect,
        "inputs": [i.dict() for i in req.inputs],
    }
    return tts_training_flow(man)


class PreflightResponse(BaseModel):
    hours_estimated: float
    storage_gib_estimated: float


@app.post("/preflight/youtube", response_model=PreflightResponse)
def preflight_youtube(url: str):
    # TODO: probe metadata; stubbed for now
    return PreflightResponse(hours_estimated=1.0, storage_gib_estimated=0.8)
