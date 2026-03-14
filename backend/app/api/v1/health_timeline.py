import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.health import HealthEvent, Prescription
from app.schemas.health import (
    HealthEventOut, HealthEventCreate,
    PrescriptionOut, PrescriptionCreate, PrescriptionUpdate,
)
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/timeline", response_model=list[HealthEventOut])
async def get_timeline(
    event_type: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(HealthEvent).where(HealthEvent.user_id == current_user.id)

    if event_type:
        query = query.where(HealthEvent.event_type == event_type)
    if start_date:
        query = query.where(HealthEvent.event_date >= start_date)
    if end_date:
        query = query.where(HealthEvent.event_date <= end_date)

    query = query.order_by(HealthEvent.event_date.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/events", response_model=HealthEventOut, status_code=201)
async def create_health_event(
    body: HealthEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = HealthEvent(
        user_id=current_user.id,
        event_type=body.event_type,
        title=body.title,
        description=body.description,
        event_date=body.event_date,
        severity=body.severity,
        metadata_=body.metadata_,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=204)
async def delete_health_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthEvent).where(
            HealthEvent.id == event_id, HealthEvent.user_id == current_user.id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Health event")
    await db.delete(event)
    await db.commit()


# ─── Prescriptions ────────────────────────────────────────────────────────────

@router.get("/prescriptions", response_model=list[PrescriptionOut])
async def list_prescriptions(
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Prescription).where(Prescription.user_id == current_user.id)
    if status:
        query = query.where(Prescription.status == status)
    query = query.order_by(Prescription.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/prescriptions", response_model=PrescriptionOut, status_code=201)
async def create_prescription(
    body: PrescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rx = Prescription(user_id=current_user.id, **body.model_dump())
    db.add(rx)
    await db.commit()
    await db.refresh(rx)
    return rx


@router.patch("/prescriptions/{rx_id}", response_model=PrescriptionOut)
async def update_prescription(
    rx_id: uuid.UUID,
    body: PrescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription).where(
            Prescription.id == rx_id, Prescription.user_id == current_user.id
        )
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise NotFoundError("Prescription")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rx, key, value)

    await db.commit()
    await db.refresh(rx)
    return rx


@router.delete("/prescriptions/{rx_id}", status_code=204)
async def delete_prescription(
    rx_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription).where(
            Prescription.id == rx_id, Prescription.user_id == current_user.id
        )
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise NotFoundError("Prescription")
    await db.delete(rx)
    await db.commit()
