"""GET /api/admin — list inquiries + bookings (HTTP Basic auth via env)."""
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Inquiry

router = APIRouter(prefix="/api", tags=["admin"])
security = HTTPBasic()

INQUIRY_STATUSES = ["pending", "processing", "completed", "cancelled"]
BOOKING_STATUSES = ["new", "contacted", "closed"]


class StatusUpdate(BaseModel):
    status: str


def _require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    user = os.getenv("ADMIN_USERNAME", "admin")
    pw = os.getenv("ADMIN_PASSWORD", "change-me")
    ok_user = secrets.compare_digest(credentials.username, user)
    ok_pw = secrets.compare_digest(credentials.password, pw)
    if not (ok_user and ok_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _inquiry_dict(i: Inquiry):
    return {
        "id": i.id,
        "first_name": i.first_name,
        "last_name": i.last_name,
        "name": f"{i.first_name} {i.last_name}".strip(),
        "phone": i.phone,
        "email": i.email,
        "company": i.company,
        "address": i.address,
        "city": i.city,
        "state": i.state,
        "zip": i.zip,
        "country": i.country,
        "freight_region": i.freight_region,
        "contact_pref": i.contact_pref,
        "best_time": i.best_time,
        "payment_method": i.payment_method,
        "notes": i.notes,
        "items": i.items or [],
        "total": i.total,
        "status": i.status,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _booking_dict(b: Booking):
    return {
        "id": b.id,
        "first_name": b.first_name,
        "last_name": b.last_name,
        "name": f"{b.first_name} {b.last_name}".strip(),
        "phone": b.phone,
        "email": b.email,
        "service": b.service,
        "product_interest": b.product_interest,
        "details": b.details,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("/admin")
def admin_data(
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    inquiries = db.query(Inquiry).order_by(Inquiry.created_at.desc()).all()
    bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
    return {
        "inquiries": [_inquiry_dict(i) for i in inquiries],
        "bookings": [_booking_dict(b) for b in bookings],
        "counts": {"inquiries": len(inquiries), "bookings": len(bookings)},
        "statuses": {"inquiries": INQUIRY_STATUSES, "bookings": BOOKING_STATUSES},
    }


@router.patch("/admin/inquiries/{item_id}")
def update_inquiry_status(
    item_id: int,
    payload: StatusUpdate,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(Inquiry).filter(Inquiry.id == item_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    rec.status = payload.status
    db.commit()
    return {"ok": True, "id": item_id, "status": rec.status}


@router.delete("/admin/inquiries/{item_id}")
def delete_inquiry(
    item_id: int,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(Inquiry).filter(Inquiry.id == item_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    db.delete(rec)
    db.commit()
    return {"ok": True, "id": item_id}


@router.patch("/admin/bookings/{item_id}")
def update_booking_status(
    item_id: int,
    payload: StatusUpdate,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(Booking).filter(Booking.id == item_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Booking not found")
    rec.status = payload.status
    db.commit()
    return {"ok": True, "id": item_id, "status": rec.status}


@router.delete("/admin/bookings/{item_id}")
def delete_booking(
    item_id: int,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(Booking).filter(Booking.id == item_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(rec)
    db.commit()
    return {"ok": True, "id": item_id}
