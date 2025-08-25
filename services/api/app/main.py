from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .classify import apply_rules
from .config import settings
from .database import engine, get_db
from .models import Base, Rule, Transaction
from .notion import NotionClient
from .schemas import OCRWebhook, TransactionCreate, TransactionRead

# Create tables on startup (for demo/testing purposes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinTrack API")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

notion_client: Optional[NotionClient] = None
if settings.enable_notion and settings.notion_token and settings.notion_database_id:
    notion_client = NotionClient(settings.notion_token, settings.notion_database_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    transactions = db.execute(select(Transaction).order_by(Transaction.id.desc())).scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "transactions": transactions})


@app.post("/transactions", response_model=TransactionRead)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    tx = Transaction(**payload.dict())
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if tx.category_id is None:
        rules = db.execute(select(Rule).where(Rule.user_id == tx.user_id)).scalars().all()
        rule_dicts = [r.__dict__ for r in rules]
        cat = apply_rules(rule_dicts, {"merchant": tx.merchant, "note": tx.note, "amount": float(tx.amount)})
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
        cat = apply_rules(rule_dicts, {"merchant": tx.merchant, "note": tx.note, "amount": float(tx.amount)})
        if cat:
            tx.category_id = cat
            db.add(tx)
            db.commit()
            db.refresh(tx)

    if notion_client:
        notion_client.create_transaction({"id": tx.id, "amount": float(tx.amount), "merchant": tx.merchant})

    return tx
