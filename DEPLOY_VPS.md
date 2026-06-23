# Deploy on a Hostinger VPS (Ubuntu + Nginx)

Adds this app alongside your existing Nginx sites. Runs gunicorn on an internal
port via systemd; Nginx reverse-proxies your domain to it and serves `/static/`
directly. SQLite lives on the VPS disk, so **orders persist across restarts**.

> Replace `YOURDOMAIN.com` with your real domain everywhere below.

---

## 1. Get the code on the server
```bash
sudo mkdir -p /var/www/prestige
sudo chown -R "$USER":"$USER" /var/www/prestige
git clone https://github.com/realllbadman/prestigeoutdoors.git /var/www/prestige
cd /var/www/prestige
```

## 2. Python venv + dependencies
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 3. Create the production `.env` (NOT in git — make it by hand)
```bash
nano /var/www/prestige/.env
```
Paste (use a **freshly rotated** Gmail app password + admin password):
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=prestigeoutdoorssupply@gmail.com
SMTP_PASSWORD=your-new-gmail-app-password
OWNER_EMAIL=prestigeoutdoorssupply@gmail.com
BUSINESS_NAME=Prestige Outdoors Supply
BUSINESS_EMAIL=prestigeoutdoorssupply@gmail.com
OWNER_PHONE=+1 (213) 218-0651
BUSINESS_ADDRESS=1180 N Mountain Ave, Ontario, CA 91762
ADMIN_USERNAME=Moneymind
ADMIN_PASSWORD=your-new-strong-admin-password
DATABASE_URL=sqlite:////var/www/prestige/blinds.db
```
> Note the **four slashes** in `sqlite:////var/...` = absolute path.

Quick boot test (Ctrl+C after you see `catalog synced … 80 total`):
```bash
.venv/bin/gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8004
```

## 4. Run it as a service (auto-start + auto-restart)
```bash
# let the web user own the app so it can write blinds.db
sudo chown -R www-data:www-data /var/www/prestige
sudo nano /etc/systemd/system/prestige.service
```
```ini
[Unit]
Description=Prestige Outdoors Supply (FastAPI)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/prestige
ExecStart=/var/www/prestige/.venv/bin/gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8004
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now prestige
sudo systemctl status prestige      # should be "active (running)"
curl -s localhost:8004/health        # -> {"ok":true}
```
> The app reads `.env` itself (via `load_dotenv`) from `WorkingDirectory`, so no
> systemd `EnvironmentFile` is needed.

## 5. Nginx reverse proxy
```bash
sudo nano /etc/nginx/sites-available/prestige
```
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name YOURDOMAIN.com www.YOURDOMAIN.com;

    client_max_body_size 10M;

    location /static/ {
        alias /var/www/prestige/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8004;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/prestige /etc/nginx/sites-enabled/
sudo nginx -t          # test config
sudo systemctl reload nginx
```

## 6. Point DNS + enable HTTPS
1. In your domain's DNS: **A record** `YOURDOMAIN.com` → your VPS IP (and `www` → same IP, or a CNAME to root). Wait for it to resolve.
2. Issue the cert (auto-edits Nginx to add HTTPS + redirect):
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOURDOMAIN.com -d www.YOURDOMAIN.com
```
Certbot auto-renews via a systemd timer.

## 7. Post-deploy checks
- Open `https://YOURDOMAIN.com` — padlock shows, pages load.
- Submit a **test order** + a **quote** → email arrives at `prestigeoutdoorssupply@gmail.com` and appears in `https://YOURDOMAIN.com/admin` (Basic Auth: Moneymind / your admin pw).
- Tawk chat bubble connects (check your Tawk dashboard).

## 8. Nightly database backup (cron)
```bash
sudo crontab -e
# add:
0 3 * * * sqlite3 /var/www/prestige/blinds.db ".backup '/var/backups/blinds-$(date +\%F).db'"
```

## Updating later
```bash
cd /var/www/prestige && sudo -u www-data git pull && \
sudo .venv/bin/pip install -r requirements.txt && \
sudo systemctl restart prestige
```
