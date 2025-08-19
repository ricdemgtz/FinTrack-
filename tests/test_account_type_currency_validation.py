import os
import sys
import pathlib
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from app import create_app, db


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    if os.path.exists('test.db'):
        os.remove('test.db')


def register(client):
    client.post('/auth/register', data={'email': 'test@example.com', 'password': 'pass'}, follow_redirects=True)


def test_invalid_account_type_currency(client):
    register(client)
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'invalid'})
    assert res.status_code == 422
    assert res.get_json()['errors']['type'] == ['invalid']
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'cash', 'currency': 'EUR'})
    assert res.status_code == 422
    assert res.get_json()['errors']['currency'] == ['invalid']
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'cash', 'currency': 'USD'})
    assert res.status_code == 201
    acc_id = res.get_json()['data']['id']
    res = client.put(f'/api/accounts/{acc_id}', json={'type': 'nope'})
    assert res.status_code == 422
    assert res.get_json()['errors']['type'] == ['invalid']
    res = client.put(f'/api/accounts/{acc_id}', json={'currency': 'EUR'})
    assert res.status_code == 422
    assert res.get_json()['errors']['currency'] == ['invalid']

