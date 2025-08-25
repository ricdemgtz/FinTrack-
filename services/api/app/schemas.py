from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    user_id: int
    account_id: int
    amount: float
    merchant: Optional[str] = None
    note: Optional[str] = None
    category_id: Optional[int] = None
    date: date = Field(default_factory=date.today)
    source: str = "manual"


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class OCRWebhook(TransactionBase):
    """Payload sent by OCR service via webhook."""

    source: str = "ocr"
    note: Optional[str] = Field(default="(OCR)")
