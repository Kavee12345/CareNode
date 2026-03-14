from pydantic import BaseModel
from datetime import datetime, date
import uuid


class HealthEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    description: str | None
    event_date: date
    severity: str | None
    metadata_: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class HealthEventCreate(BaseModel):
    event_type: str
    title: str
    description: str | None = None
    event_date: date
    severity: str | None = None
    metadata_: dict = {}


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    medication_name: str
    dosage: str | None
    frequency: str | None
    start_date: date | None
    end_date: date | None
    prescribing_doctor: str | None
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    medication_name: str
    dosage: str | None = None
    frequency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    prescribing_doctor: str | None = None
    notes: str | None = None


class PrescriptionUpdate(BaseModel):
    dosage: str | None = None
    frequency: str | None = None
    end_date: date | None = None
    status: str | None = None
    notes: str | None = None


class AgentOut(BaseModel):
    id: uuid.UUID
    name: str
    system_prompt_override: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt_override: str | None = None
