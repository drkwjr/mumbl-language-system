from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Optional, Dict, Literal
from datetime import datetime

class G2PRule(BaseModel):
    pattern: str
    ipa: str
    conditions: Optional[Dict[str, str]] = None
    priority: int = 0

class G2POverride(BaseModel):
    word: str
    ipa: str
    dialect: Optional[str] = None
    notes: Optional[str] = None

class TTSDefaults(BaseModel):
    speaking_rate: float = Field(1.0, ge=0.5, le=1.8)
    pitch_bias: float = Field(0.0, ge=-12, le=12)
    pause_bias: float = Field(0.1, ge=0.0, le=1.0)
    filler_bias: float = Field(0.05, ge=0.0, le=1.0)

class CurationTargets(BaseModel):
    min_minutes_90: float = 0.0
    phoneme_coverage: float = Field(0.9, ge=0.0, le=1.0)
    target_dialect_mix: Optional[Dict[str, float]] = None

class LanguageProfileV1(BaseModel):
    language: str
    dialect: str
    script: str
    version: str = "1.0.0"
    updated_at: Optional[datetime] = None
    phoneme_inventory: List[str]
    g2p_rules: List[G2PRule] = []
    g2p_overrides: List[G2POverride] = []
    lexicon_refs: List[str] = []
    register_defaults: Dict[str, float] = {"formal": 0.3, "informal": 0.7}
    style_tokens: List[str] = ["calm","conversational","storytelling"]
    emotion_tokens: List[str] = ["neutral","excited","reassuring"]
    tts_defaults: TTSDefaults = TTSDefaults()
    fallback_chain: List[str] = []
    curation_targets: CurationTargets = CurationTargets()
    tts_strategy: Literal["standalone","grouped","cloud_fallback"] = "standalone"

    @validator("version")
    def semver(cls, v):
        import re
        assert re.match(r"^\d+\.\d+\.\d+$", v), "version must be semver"
        return v

    @validator("register_defaults")
    def probs_sum_to_one(cls, v):
        s = sum(v.values())
        assert abs(s - 1.0) < 1e-6, "register_defaults must sum to 1.0"
        return v

    @model_validator(mode='after')
    def no_cycles_in_fallback(self):
        dialect = self.dialect
        chain = self.fallback_chain
        assert dialect not in chain, "fallback_chain cannot include self"
        return self
