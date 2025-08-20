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


def test_no_duplicate_active_accounts(client):
    register(client)
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'cash'})
    assert res.status_code == 201
    acc_id = res.get_json()['data']['id']
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'cash'})
    assert res.status_code == 409
    client.delete(f'/api/accounts/{acc_id}')
    res = client.post('/api/accounts', json={'name': 'Cash', 'type': 'cash'})
    assert res.status_code == 201
    res_restore = client.post(f'/api/accounts/{acc_id}/restore')
    assert res_restore.status_code == 409


def test_no_duplicate_active_categories(client):
    register(client)
    res = client.post('/api/categories', json={'name': 'Food', 'kind': 'expense'})
    assert res.status_code == 201
    cat_id = res.get_json()['data']['id']
    res = client.post('/api/categories', json={'name': 'Food', 'kind': 'expense'})
    assert res.status_code == 409
    client.delete(f'/api/categories/{cat_id}?confirm=true')
    res = client.post('/api/categories', json={'name': 'Food', 'kind': 'expense'})
    assert res.status_code == 201
    res_restore = client.post(f'/api/categories/{cat_id}/restore')
    assert res_restore.status_code == 409

    res_sys = client.post('/api/categories', json={'name': 'Sys', 'kind': 'expense', 'is_system': True})
    assert res_sys.status_code == 201
    res_user = client.post('/api/categories', json={'name': 'Sys', 'kind': 'expense'})
    assert res_user.status_code == 201
    res_user_dup = client.post('/api/categories', json={'name': 'Sys', 'kind': 'expense'})
    assert res_user_dup.status_code == 409
