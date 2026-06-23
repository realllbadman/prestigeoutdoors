# Deploying Prestige Outdoors Supply

FastAPI + SQLite + Jinja. The app listens on `$PORT` (defaults to 8004) and
auto-creates + seeds the catalog (80 products) on first boot.

## 1. Environment variables (set on the host — never commit `.env`)

| Variable | Example |
|---|---|
| `BUSINESS_NAME` | `Prestige Outdoors Supply` |
| `BUSINESS_EMAIL` | `prestigeoutdoorssupply@gmail.com` |
| `OWNER_EMAIL` | `prestigeoutdoorssupply@gmail.com` |
| `OWNER_PHONE` | `+1 (213) 218-0651` |
| `BUSINESS_ADDRESS` | `1180 N Mountain Ave, Ontario, CA 91762` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `prestigeoutdoorssupply@gmail.com` |
| `SMTP_PASSWORD` | *(Gmail app password)* |
| `ADMIN_USERNAME` | `Moneymind` |
| `ADMIN_PASSWORD` | *(strong password)* |
| `DATABASE_URL` | `sqlite:////data/blinds.db` *(persistent path!)* |

> If `BUSINESS_NAME` isn't set it falls back to an old default — always set it.

## 2. Start command

```
gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT
```

## Option A — Docker (Fly.io, Render, Railway, any VPS)

```bash
docker build -t prestige .
docker run -p 8004:8004 --env-file .env -v "$PWD/data:/data" prestige
```
The `-v .../data:/data` mount keeps `blinds.db` (your orders) across restarts;
`DATABASE_URL` already points at `/data/blinds.db` in the image.

## Option B — Buildpack host (Render / Railway)

- Build: `pip install -r requirements.txt`
- Start: taken from the `Procfile` automatically.
- Add a **Persistent Disk** mounted at `/data` and set
  `DATABASE_URL=sqlite:////data/blinds.db` (otherwise orders are wiped on deploy).

## 3. After deploy — required checks

- **HTTPS must be on** — the `/admin` dashboard uses HTTP Basic auth.
- Submit a test order **and** quote → confirm the email arrives at
  `prestigeoutdoorssupply@gmail.com` and shows in `/admin`.
- **Back up `blinds.db`** regularly — it holds all orders & bookings.
- Confirm the Tawk.to chat widget connects (log into your Tawk dashboard).
