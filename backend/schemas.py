"""Pydantic request/response schemas."""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class CartItem(BaseModel):
    slug: Optional[str] = ""
    name: str
    price: float = 0.0
    qty: int = 1
    image: Optional[str] = ""


class InquiryCreate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    company: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "United States"
    freight_region: str = ""
    contact_pref: str = "Phone Call"
    best_time: str = ""
    payment_method: str = "Bank Transfer"
    notes: str = ""
    items: List[CartItem] = Field(default_factory=list)
    total: float = 0.0


class BookingCreate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    service: str = "General Inquiry"
    product_interest: str = ""
    details: str = ""


class MessageOut(BaseModel):
    ok: bool = True
    message: str = "Received"
    id: Optional[int] = None
