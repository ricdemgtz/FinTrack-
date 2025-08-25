import os
import json
import hmac
import hashlib
import pathlib

import pytest
from fastapi.testclient import TestClient

# set environment before importing app
os.environ['DATABASE_URL'] = 'sqlite:///test_ocr.db'
os.environ['WEBHOOK_SECRET'] = 'testsecret'

from services.api.app.main import app  # noqa: E402
from services.api.app.database import SessionLocal, engine  # noqa: E402
from services.api.app.models import Base, User, Account, Category, Rule, Transaction, Attachment  # noqa: E402

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    db_path = pathlib.Path('test_ocr.db')
    if db_path.exists():
        db_path.unlink()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _create_sample_data():
    db = SessionLocal()
    user = User(email='u@example.com', password_hash='x')
    db.add(user)
    db.commit(); db.refresh(user)
    acc = Account(user_id=user.id, name='Cash', type='cash', currency='MXN', opening_balance=0)
    db.add(acc)
    cat = Category(user_id=user.id, name='Food', kind='expense')
    db.add(cat)
    db.commit(); db.refresh(acc); db.refresh(cat)
    rule = Rule(user_id=user.id, pattern='Shop', field='merchant', category_id=cat.id)
    db.add(rule); db.commit(); db.refresh(rule)
    tx = Transaction(user_id=user.id, account_id=acc.id, amount=10, merchant='Shop', note='x')
    db.add(tx); db.commit(); db.refresh(tx)
    att = Attachment(user_id=user.id, transaction_id=tx.id, filename='a.jpg')
    db.add(att); db.commit(); db.refresh(att)
    db.close()
    return att.id, tx.id, cat.id


def test_webhook_valid_signature(client):
    att_id, tx_id, cat_id = _create_sample_data()
    body = json.dumps({'attachment_id': att_id, 'text': 'hello'}).encode()
    sig = hmac.new(b'testsecret', body, hashlib.sha256).hexdigest()
    res = client.post('/webhooks/ocr', data=body, headers={'X-Signature': sig})
    assert res.status_code == 200
    db = SessionLocal()
    att = db.get(Attachment, att_id)
    tx = db.get(Transaction, tx_id)
    assert att.ocr_text == 'hello'
    assert tx.category_id == cat_id
    db.close()


def test_webhook_invalid_signature(client):
    att_id, tx_id, cat_id = _create_sample_data()
    body = json.dumps({'attachment_id': att_id, 'text': 'hello'}).encode()
    res = client.post('/webhooks/ocr', data=body, headers={'X-Signature': 'bad'})
    assert res.status_code == 400
