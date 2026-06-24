"""FastAPI application: lifespan seeding, no-cache middleware, page routes."""
import os
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime

# Load environment BEFORE importing backend modules that read os.getenv().
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.database import Base, SessionLocal, engine, get_db  # noqa: E402
from backend.models import Product  # noqa: E402
from backend.routes import admin as admin_routes  # noqa: E402
from backend.routes import bookings as bookings_routes  # noqa: E402
from backend.routes import inquiries as inquiries_routes  # noqa: E402
from backend.seed_data import (  # noqa: E402
    CATEGORY_LABELS,
    CATEGORY_SUBCATEGORIES,
    FEATURED_SLUGS,
    SLIDER_CHIPS,
    sync_products,
)

# --------------------------------------------------------------------------- #
#  Paths & business config                                                    #
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

ASSET_VERSION = "15"  # bump to bust static asset caches

BUSINESS = {
    "name": os.getenv("BUSINESS_NAME", "Deer Blinds & Stands Co"),
    "email": os.getenv("BUSINESS_EMAIL", os.getenv("OWNER_EMAIL", "sales@example.com")),
    "phone": os.getenv("OWNER_PHONE", "+1 (555) 123-4567"),
    "address": os.getenv("BUSINESS_ADDRESS", "1234 Ridgeline Rd, Huntsville, TX 77320"),
    "hours": "Mon–Sat 8am–7pm PT · Sun by appointment",
    "free_ship_threshold": 1500,
    "flat_shipping": 14.99,
}

# International freight added by region (flat, higher than domestic). JS mirrors this.
FREIGHT_REGIONS = OrderedDict([
    ("United States (Domestic)", 0),
    ("Canada", 250),
    ("Mexico", 250),
    ("Europe", 600),
    ("United Kingdom", 600),
    ("Asia", 750),
    ("Middle East", 800),
    ("Australia / New Zealand", 850),
    ("South America", 800),
    ("Other International", 900),
])

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

# --------------------------------------------------------------------------- #
#  Jinja environment (cache_size=0 — see spec) + globals                      #
# --------------------------------------------------------------------------- #
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    cache_size=0,
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)
templates = Jinja2Templates(env=jinja_env)

jinja_env.globals.update(
    BUSINESS=BUSINESS,
    CATEGORY_LABELS=CATEGORY_LABELS,
    CATEGORY_SUBCATEGORIES=CATEGORY_SUBCATEGORIES,
    SLIDER_CHIPS=SLIDER_CHIPS,
    FREIGHT_REGIONS=FREIGHT_REGIONS,
    US_STATES=US_STATES,
    ASSET_VERSION=ASSET_VERSION,
    current_year=datetime.now().year,
    # Resolve a product image: full http(s) URL used as-is, bare filename
    # served from /static/images/.
    img_url=lambda img: img if str(img).startswith(("http://", "https://"))
    else f"/static/images/{img}",
)


# --------------------------------------------------------------------------- #
#  Migrations + seeding on startup                                            #
# --------------------------------------------------------------------------- #
def _run_migrations():
    """Idempotent ALTER TABLE migrations (older DBs may miss newer columns)."""
    statements = [
        "ALTER TABLE products ADD COLUMN subcategory VARCHAR",
        "ALTER TABLE products ADD COLUMN model_number VARCHAR",
        "ALTER TABLE products ADD COLUMN price_max FLOAT",
        "ALTER TABLE products ADD COLUMN original_price FLOAT",
        "ALTER TABLE products ADD COLUMN badge VARCHAR",
        "ALTER TABLE products ADD COLUMN images JSON",
        "ALTER TABLE inquiries ADD COLUMN freight_region VARCHAR",
        "ALTER TABLE inquiries ADD COLUMN company VARCHAR",
        "ALTER TABLE bookings ADD COLUMN product_interest VARCHAR",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()  # column already exists — ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    db = SessionLocal()
    try:
        sync_products(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Deer Blinds & Stands Co", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    """Disable caching of server-rendered HTML; static assets keep ?v= busting."""
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if ctype.startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(inquiries_routes.router)
app.include_router(bookings_routes.router)
app.include_router(admin_routes.router)


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _interleave_by_category(products):
    """Round-robin across categories so one category doesn't clump."""
    groups = OrderedDict()
    for p in products:
        groups.setdefault(p.category, []).append(p)
    out = []
    lists = list(groups.values())
    while any(lists):
        for lst in lists:
            if lst:
                out.append(lst.pop(0))
    return out


def _brand_counts(db, limit=10):
    from sqlalchemy import func
    q = (
        db.query(Product.brand, func.count(Product.id))
        .filter(Product.brand != "")
        .group_by(Product.brand)
        .order_by(func.count(Product.id).desc())
    )
    return [(b, c) for b, c in q.all()][:limit]


def _category_counts(db):
    from sqlalchemy import func
    rows = dict(
        db.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .all()
    )
    return rows


# --------------------------------------------------------------------------- #
#  Page routes                                                                 #
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    # "Best Blinds" grid — a spread of blinds from cheapest to most expensive,
    # so budget shoppers see affordable options first and premium shoppers see
    # the high end as they scroll. Sampled evenly across the price range.
    blinds_asc = (
        db.query(Product)
        .filter(Product.category == "deer-blinds-stands", Product.price >= 900)
        .order_by(Product.price.asc())
        .all()
    )
    n = len(blinds_asc)
    if n > 8:
        # evenly sample 8 across the whole range so the cheapest AND the most
        # expensive both appear, in ascending order.
        idxs = sorted({round(i * (n - 1) / 7) for i in range(8)})
        featured = [blinds_asc[i] for i in idxs]
    else:
        featured = blinds_asc

    # Hero cards favour real product photography (non-placeholder) for visual punch.
    hero_blinds = (
        db.query(Product)
        .filter(Product.category == "deer-blinds-stands", Product.image != "placeholder.jpg")
        .order_by(Product.price.desc())
        .limit(4)
        .all()
    )
    if len(hero_blinds) < 4:
        hero_blinds = featured[:4]

    # Flagship blind spotlighted in a dedicated band (falls back gracefully).
    spotlight = (
        db.query(Product).filter(Product.slug == "camo-steel-blind-6x6").first()
        or db.query(Product)
        .filter(Product.category == "deer-blinds-stands", Product.image != "placeholder.jpg")
        .first()
    )

    cat_counts = _category_counts(db)
    total = db.query(Product).count()
    context = {
        "featured": featured[:8],
        "hero_blinds": hero_blinds,
        "spotlight": spotlight,
        "brand_counts": _brand_counts(db, limit=8),
        "category_counts": cat_counts,
        "total_products": total,
        "num_categories": len(CATEGORY_LABELS),
        "num_states": 50,
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/products", response_class=HTMLResponse)
def products(
    request: Request,
    q: str = "",
    category: str = "",
    subcategory: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if subcategory:
        query = query.filter(Product.subcategory == subcategory)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Product.name.ilike(like))
            | (Product.brand.ilike(like))
            | (Product.description.ilike(like))
            | (Product.model_number.ilike(like))
        )

    results = query.all()
    # When unfiltered, interleave categories so the grid feels mixed.
    if not (category or subcategory or q):
        results = _interleave_by_category(results)
    else:
        results = sorted(results, key=lambda p: p.price)   # cheapest → most expensive

    context = {
        "products": results,
        "result_count": len(results),
        "q": q,
        "active_category": category,
        "active_subcategory": subcategory,
        "category_label": CATEGORY_LABELS.get(category, "All Products"),
        "subcategories": CATEGORY_SUBCATEGORIES.get(category, []),
        "category_counts": _category_counts(db),
    }
    return templates.TemplateResponse(request, "products.html", context)


@app.get("/products/{slug}", response_class=HTMLResponse)
def product_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        return templates.TemplateResponse(
            request, "products.html",
            {
                "products": [],
                "result_count": 0,
                "q": "",
                "active_category": "",
                "active_subcategory": "",
                "category_label": "Product not found",
                "subcategories": [],
                "category_counts": _category_counts(db),
                "not_found_slug": slug,
            },
            status_code=404,
        )
    related = (
        db.query(Product)
        .filter(Product.category == product.category, Product.id != product.id)
        .limit(8)
        .all()
    )
    context = {
        "product": product,
        "related": related[:4],
        "category_label": CATEGORY_LABELS.get(product.category, ""),
        "financing_months": 36,
    }
    return templates.TemplateResponse(request, "product_detail.html", context)


@app.get("/checkout", response_class=HTMLResponse)
def checkout(request: Request):
    return templates.TemplateResponse(request, "checkout.html", {})


@app.get("/financing", response_class=HTMLResponse)
def financing(request: Request):
    return templates.TemplateResponse(request, "financing.html", {})


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", {})


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {})


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


@app.get("/health")
def health():
    return {"ok": True}
