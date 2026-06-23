"""Email notifications via aiosmtplib over Gmail SMTP (STARTTLS:587).

The app password may contain spaces when copied from Google — they are
stripped before use. If SMTP is not configured, sending fails gracefully
(logs a warning) so the site keeps working without email.
"""
import os
from datetime import datetime
from email.message import EmailMessage

import aiosmtplib


def _cfg():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        # Gmail app passwords are shown with spaces; strip them.
        "password": (os.getenv("SMTP_PASSWORD", "") or "").replace(" ", ""),
        "owner": os.getenv("OWNER_EMAIL") or os.getenv("BUSINESS_EMAIL", ""),
        "business": os.getenv("BUSINESS_NAME", "Deer Blinds & Stands Co"),
    }


def _is_configured(cfg):
    return bool(cfg["host"] and cfg["user"] and cfg["password"] and cfg["owner"])


async def _send(subject, html, reply_to=None):
    cfg = _cfg()
    if not _is_configured(cfg):
        print(f"[email] SMTP not configured — skipping send: {subject!r}")
        return False

    msg = EmailMessage()
    msg["From"] = f"{cfg['business']} <{cfg['user']}>"
    msg["To"] = cfg["owner"]
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content("This message requires an HTML-capable email client.")
    msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=cfg["host"],
            port=cfg["port"],
            start_tls=True,
            username=cfg["user"],
            password=cfg["password"],
            timeout=20,
        )
        print(f"[email] sent: {subject!r} -> {cfg['owner']}")
        return True
    except Exception as exc:  # fail gracefully
        print(f"[email] send FAILED ({type(exc).__name__}): {exc}")
        return False


# --------------------------------------------------------------------------- #
#  HTML helpers                                                               #
# --------------------------------------------------------------------------- #
ACCENT = "#e8540b"
INK = "#1c1c1a"


def _shell(title, rows_html, items_html=""):
    business = _cfg()["business"]
    stamp = datetime.now().strftime("%b %d, %Y · %I:%M %p")
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;background:#f4f3f0;padding:24px;color:{INK}">
  <div style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #e2ded7;border-radius:12px;overflow:hidden">
    <div style="background:{INK};padding:20px 24px">
      <div style="color:#fff;font-size:20px;font-weight:800;letter-spacing:.5px;text-transform:uppercase">{business}</div>
      <div style="color:{ACCENT};font-size:13px;font-weight:700;margin-top:4px;text-transform:uppercase;letter-spacing:1px">{title}</div>
    </div>
    <div style="padding:24px">
      <table style="width:100%;border-collapse:collapse;font-size:14px">{rows_html}</table>
      {items_html}
      <p style="color:#8a857c;font-size:12px;margin-top:24px">Received {stamp}</p>
    </div>
  </div>
</div>"""


def _row(label, value):
    if value is None or value == "":
        value = "—"
    return (
        f'<tr><td style="padding:7px 0;color:#8a857c;width:38%;vertical-align:top;'
        f'border-bottom:1px solid #f0ece5">{label}</td>'
        f'<td style="padding:7px 0;font-weight:600;border-bottom:1px solid #f0ece5">{value}</td></tr>'
    )


def _items_table(items, total):
    if not items:
        return ""
    rows = ""
    for it in items:
        name = getattr(it, "name", None) or (it.get("name") if isinstance(it, dict) else "Item")
        qty = getattr(it, "qty", None) or (it.get("qty") if isinstance(it, dict) else 1)
        price = getattr(it, "price", None) or (it.get("price") if isinstance(it, dict) else 0)
        line = float(price or 0) * int(qty or 1)
        rows += (
            f'<tr><td style="padding:8px 0;border-bottom:1px solid #f0ece5">{name}</td>'
            f'<td style="padding:8px 0;border-bottom:1px solid #f0ece5;text-align:center">×{qty}</td>'
            f'<td style="padding:8px 0;border-bottom:1px solid #f0ece5;text-align:right">${line:,.2f}</td></tr>'
        )
    return f"""
      <h3 style="margin:24px 0 8px;font-size:15px;text-transform:uppercase;letter-spacing:.5px">Requested Items</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        {rows}
        <tr><td style="padding:12px 0;font-weight:800" colspan="2">Estimated Total</td>
        <td style="padding:12px 0;font-weight:800;text-align:right;color:{ACCENT}">${float(total or 0):,.2f}</td></tr>
      </table>
      <p style="color:#8a857c;font-size:12px;margin-top:8px">
        Totals are estimates — freight, availability &amp; final pricing confirmed by phone/email.</p>"""


# --------------------------------------------------------------------------- #
#  Public senders                                                             #
# --------------------------------------------------------------------------- #
async def send_inquiry_email(data):
    """data: InquiryCreate (Pydantic) or dict-like with the same fields."""
    g = (lambda k, d="": getattr(data, k, None) if hasattr(data, k) else None) if not isinstance(data, dict) \
        else (lambda k, d="": data.get(k, d))

    name = f"{g('first_name')} {g('last_name')}".strip() or "—"
    rows = (
        _row("Customer", name)
        + _row("Phone", g("phone"))
        + _row("Email", g("email"))
        + _row("Company", g("company"))
        + _row("Address", g("address"))
        + _row("City / State / ZIP", f"{g('city')}, {g('state')} {g('zip')}".strip(" ,"))
        + _row("Country", g("country"))
        + _row("Freight Region", g("freight_region"))
        + _row("Preferred Contact", g("contact_pref"))
        + _row("Best Time", g("best_time"))
        + _row("Payment Method", g("payment_method"))
        + _row("Notes", g("notes"))
    )
    items = getattr(data, "items", None) if not isinstance(data, dict) else data.get("items")
    total = getattr(data, "total", None) if not isinstance(data, dict) else data.get("total")
    html = _shell("New Order / Quote Request", rows, _items_table(items, total))
    return await _send(f"New Order / Quote — {name}", html, reply_to=g("email") or None)


async def send_booking_email(data):
    """data: BookingCreate (Pydantic) or dict-like."""
    g = (lambda k, d="": getattr(data, k, None)) if not isinstance(data, dict) \
        else (lambda k, d="": data.get(k, d))

    name = f"{g('first_name')} {g('last_name')}".strip() or "—"
    rows = (
        _row("Name", name)
        + _row("Phone", g("phone"))
        + _row("Email", g("email"))
        + _row("Service", g("service"))
        + _row("Product Interest", g("product_interest"))
        + _row("Details", g("details"))
    )
    html = _shell("New Install / Consultation Request", rows)
    return await _send(f"New Booking — {g('service') or 'Inquiry'} — {name}", html, reply_to=g("email") or None)
