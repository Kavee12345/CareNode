from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
import uuid


class HealthEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    description: Optional[str]
    event_date: date
    severity: Optional[str]
    metadata_: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class HealthEventCreate(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: date
    severity: Optional[str] = None
    metadata_: dict = {}


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    medication_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    prescribing_doctor: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    medication_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribing_doctor: Optional[str] = None
    notes: Optional[str] = None


class PrescriptionUpdate(BaseModel):
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AgentOut(BaseModel):
    id: uuid.UUID
    name: str
    system_prompt_override: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt_override: Optional[str] = None
