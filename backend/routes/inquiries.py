"""POST /api/inquiries — order / quote request -> persist + email owner."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Inquiry
from backend.schemas import InquiryCreate, MessageOut
from backend.services.email import send_inquiry_email

router = APIRouter(prefix="/api", tags=["inquiries"])


@router.post("/inquiries", response_model=MessageOut)
def create_inquiry(
    payload: InquiryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    record = Inquiry(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        company=payload.company,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        zip=payload.zip,
        country=payload.country,
        freight_region=payload.freight_region,
        contact_pref=payload.contact_pref,
        best_time=payload.best_time,
        payment_method=payload.payment_method,
        notes=payload.notes,
        items=[item.model_dump() for item in payload.items],
        total=payload.total,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Email the owner in the background (fails gracefully if unconfigured).
    background_tasks.add_task(send_inquiry_email, payload)

    return MessageOut(
        ok=True,
        id=record.id,
        message="Request received. We'll contact you to finalize availability, freight & payment.",
    )
