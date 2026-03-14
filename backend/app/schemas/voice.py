from pydantic import BaseModel
from typing import List

from app.schemas.chat import MedicalResponse


class VoiceResponse(BaseModel):
    transcript: str
    response: MedicalResponse
    audio_base64: str


class TTSRequest(BaseModel):
    text: str
