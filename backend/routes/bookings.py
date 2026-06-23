"""POST /api/bookings — install / consultation request -> persist + email owner."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking
from backend.schemas import BookingCreate, MessageOut
from backend.services.email import send_booking_email

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/bookings", response_model=MessageOut)
def create_booking(
    payload: BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    record = Booking(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        service=payload.service or "General Inquiry",
        product_interest=payload.product_interest,
        details=payload.details,
        status="new",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    background_tasks.add_task(send_booking_email, payload)

    return MessageOut(
        ok=True,
        id=record.id,
        message="Thanks! We'll reach out shortly to help with your blind, install or question.",
    )
