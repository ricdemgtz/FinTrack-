import importlib
import os
import pathlib

import pytest
from httpx import AsyncClient

# configure environment for tests before importing modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bot.db")
os.environ.setdefault("API_BASE_URL", "http://test")

from services.api.app.main import app
from services.api.app.database import SessionLocal, engine
from services.api.app import models


@pytest.fixture(autouse=True)
def clean_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
    db_path = pathlib.Path("./test_bot.db")
    if db_path.exists():
        db_path.unlink()


def seed_basic_data():
    db = SessionLocal()
    user = models.User(id=1, email="user@example.com", password_hash="x")
    account = models.Account(id=1, user_id=1, name="Cash", type="cash", opening_balance=0)
    db.add_all([user, account])
    db.commit()
    db.close()


@pytest.mark.asyncio
async def test_post_transaction_integration(monkeypatch):
    seed_basic_data()
    import services.bot.main as bot_main
    importlib.reload(bot_main)

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        class MockClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return test_client

            async def __aexit__(self, exc_type, exc, tb):
                pass

        monkeypatch.setattr(bot_main.httpx, "AsyncClient", MockClient)
        await bot_main.post_transaction(12.5, "Shop", note="", income=False)

    db = SessionLocal()
    tx = db.query(models.Transaction).first()
    assert float(tx.amount) == -12.5
    assert tx.merchant == "Shop"
    db.close()


@pytest.mark.asyncio
async def test_post_transaction_income(monkeypatch):
    seed_basic_data()
    import services.bot.main as bot_main
    importlib.reload(bot_main)

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        class MockClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return test_client

            async def __aexit__(self, exc_type, exc, tb):
                pass

        monkeypatch.setattr(bot_main.httpx, "AsyncClient", MockClient)
        await bot_main.post_transaction(20, "Salary", note="", income=True)

    db = SessionLocal()
    tx = db.query(models.Transaction).first()
    assert float(tx.amount) == 20.0
    assert tx.merchant == "Salary"
    db.close()
