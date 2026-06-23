# DEER BLINDS & STANDS CO

A production-style hunting **blinds & gear** e-commerce site. Server-rendered with
FastAPI + Jinja2, SQLite via SQLAlchemy, and a vanilla-JS storefront (cart in
`localStorage`, no front-end framework). No online payment — customers submit an
order/quote request and the owner is emailed to finalize availability, freight & payment.

## Stack

- Python 3.12 (runs on 3.10+), FastAPI, Uvicorn, SQLAlchemy ORM, SQLite, Jinja2
- Email: `aiosmtplib` over Gmail SMTP (STARTTLS / 587), sent via FastAPI `BackgroundTasks`
- Config: `python-dotenv` (`.env` for secrets, `.env.example` for placeholders)

## Project layout

```
backend/        FastAPI app, models, schemas, seed catalog, routes, email service
frontend/       standalone about.html + admin.html (served as FileResponse)
templates/      Jinja templates (base, home, listing, detail, checkout, financing, contact)
static/         css/main.css, js/main.js, js/animations.js, images/
```

## Setup & run

```bash
# 1. Install deps (a virtualenv is recommended)
python3 -m pip install -r requirements.txt

# 2. Configure
cp .env.example .env        # then edit .env with your Gmail + app password

# 3. Run (DB auto-creates & seeds on startup)
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8004 --reload
```

Open <http://localhost:8004>.

## Configuration (`.env`)

| Key | Purpose |
| --- | --- |
| `SMTP_HOST` / `SMTP_PORT` | Gmail SMTP (`smtp.gmail.com` / `587`) |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail address + **App Password** (spaces are stripped) |
| `OWNER_EMAIL` | Where order/quote + booking notifications are delivered |
| `BUSINESS_NAME` / `BUSINESS_EMAIL` / `OWNER_PHONE` / `BUSINESS_ADDRESS` | Shown on the site |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Basic-Auth for `/admin` + `/api/admin` |
| `DATABASE_URL` | Defaults to `sqlite:///./blinds.db` |

Email fails gracefully: if SMTP isn't configured the request still succeeds and is
saved to the database (visible in the admin dashboard).

## Catalog / seeding

`backend/seed_data.py` is the **single source of truth**. On startup the app runs
`create_all`, idempotent `ALTER TABLE` migrations, then `sync_products(db)` which
upserts the catalog by `slug`. Edit the seed data and restart to update the live site.

## Admin

Visit `/admin` (Basic Auth using `ADMIN_USERNAME` / `ADMIN_PASSWORD`). Lists all
inquiries (orders/quotes) and bookings (install/consult requests), newest first.

## Product images

Blind & optic photos are reused from the companion "Hunting & Fishing Supply Co"
project and live in `static/images/` as bare filenames. Everything else uses
`placeholder.jpg`; swap in real photos by dropping a file into `static/images/` and
setting the product's `image` in `seed_data.py`. **Never** paste base64 data URIs into
the seed file — decode to a real file first.

## Routes

- `GET /` home · `GET /products` listing (filters: `q`, `category`, `subcategory`)
- `GET /products/{slug}` detail · `GET /checkout` · `GET /financing` · `GET /contact`
- `GET /about` · `GET /admin` (FileResponse)
- `POST /api/inquiries` · `POST /api/bookings` · `GET /api/admin` (Basic Auth)
