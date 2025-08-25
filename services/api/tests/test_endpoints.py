import os
import pathlib

import pytest
from fastapi.testclient import TestClient

# Configure test database before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api.db")

from services.api.app.main import app
from services.api.app.database import SessionLocal, engine
from services.api.app import models


@pytest.fixture(autouse=True)
def clean_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
    db_path = pathlib.Path("./test_api.db")
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client():
    return TestClient(app)


def seed_basic_data():
    db = SessionLocal()
    user = models.User(id=1, email="test@example.com", password_hash="x")
    account = models.Account(id=1, user_id=1, name="Cash", type="cash", opening_balance=0)
    category = models.Category(id=1, user_id=1, name="Food", kind="expense")
    rule = models.Rule(id=1, user_id=1, pattern="Star", category_id=1)
    db.add_all([user, account, category, rule])
    db.commit()
    db.close()


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_transactions_endpoint(client):
    seed_basic_data()
    payload = {
        "user_id": 1,
        "account_id": 1,
        "amount": -5,
        "merchant": "Starbucks",
        "note": "latte",
    }
    res = client.post("/transactions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["category_id"] == 1

    res = client.get("/transactions")
    items = res.json()
    assert len(items) == 1
    assert items[0]["merchant"] == "Starbucks"


def test_webhook_ocr_endpoint(client):
    seed_basic_data()
    payload = {
        "user_id": 1,
        "account_id": 1,
        "amount": -10,
        "merchant": "Starbucks",
    }
    res = client.post("/webhooks/ocr", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["note"] == "(OCR)"
    assert data["category_id"] == 1
