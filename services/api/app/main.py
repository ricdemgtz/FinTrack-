from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import redis.asyncio as redis
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from .classify import apply_rules
from .config import settings
from .database import engine, get_db
from .models import Base, Rule, Transaction
from .notion import NotionClient
from .schemas import OCRWebhook, TransactionCreate, TransactionRead

try:
    from pythonjsonlogger import jsonlogger
except Exception:  # pragma: no cover
    jsonlogger = None

# Create tables on startup (for demo/testing purposes)
Base.metadata.create_all(bind=engine)

# Configure JSON logging
logger = logging.getLogger()
handler = logging.StreamHandler()
if jsonlogger:
    handler.setFormatter(jsonlogger.JsonFormatter())
else:
    handler.setFormatter(logging.Formatter('{"level": "%(levelname)s", "message": "%(message)s"}'))
logger.handlers = [handler]
logger.setLevel(settings.log_level.upper())

# Redis rate limiting middleware
redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

def parse_rate(rate: str) -> tuple[int, int]:
    amount, per = rate.split('/')
    periods = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}
    return int(amount), periods.get(per, 60)

limit, period = parse_rate(settings.rate_limit)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int, period: int):
        super().__init__(app)
        self.limit = limit
        self.period = period

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        key = f"rl:{ip}"
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, self.period)
            if current > self.limit:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        except Exception:
            pass
        return await call_next(request)

app = FastAPI(title="FinTrack API")
app.add_middleware(RateLimiterMiddleware, limit=limit, period=period)

app.mount(
    "/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static"
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

notion_client: Optional[NotionClient] = None
if settings.enable_notion and settings.notion_token and settings.notion_database_id:
    notion_client = NotionClient(settings.notion_token, settings.notion_database_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    transactions = (
        db.execute(
            select(Transaction)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    balance = float(db.execute(select(func.sum(Transaction.amount))).scalar() or 0)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "transactions": transactions, "balance": balance},
    )


@app.post("/transactions", response_model=TransactionRead)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = Transaction(**payload.dict())
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if tx.category_id is None:
        rules = db.execute(select(Rule).where(Rule.user_id == tx.user_id)).scalars().all()
        rule_dicts = [r.__dict__ for r in rules]
        cat = apply_rules(
            rule_dicts, {"merchant": tx.merchant, "note": tx.note, "amount": float(tx.amount)}
        )
        if cat:
            tx.category_id = cat
            db.add(tx)
            db.commit()
            db.refresh(tx)

    if notion_client:
        notion_client.create_transaction({"id": tx.id, "amount": float(tx.amount), "merchant": tx.merchant})

    return tx


@app.get("/transactions", response_model=list[TransactionRead])
def list_transactions(db: Session = Depends(get_db), user_id: Optional[int] = None):
    stmt = select(Transaction)
    if user_id is not None:
        stmt = stmt.where(Transaction.user_id == user_id)
    items = db.execute(stmt).scalars().all()
    return items


@app.post("/webhooks/ocr", response_model=TransactionRead)
def webhook_ocr(payload: OCRWebhook, db: Session = Depends(get_db)):
    tx = Transaction(**payload.dict())
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if tx.category_id is None:
        rules = db.execute(select(Rule).where(Rule.user_id == tx.user_id)).scalars().all()
        rule_dicts = [r.__dict__ for r in rules]
        cat = apply_rules(
            rule_dicts, {"merchant": tx.merchant, "note": tx.note, "amount": float(tx.amount)}
        )
        if cat:
            tx.category_id = cat
            db.add(tx)
            db.commit()
            db.refresh(tx)

    if notion_client:
        notion_client.create_transaction({"id": tx.id, "amount": float(tx.amount), "merchant": tx.merchant})

    return tx
