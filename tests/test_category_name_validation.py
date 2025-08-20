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


def test_category_name_validation(client):
    register(client)
    res = client.post('/api/categories', json={'name': '   ', 'kind': 'expense'})
    assert res.status_code == 400
    assert res.get_json()['errors']['name'] == ['required or length']
    res = client.post('/api/categories', json={'name': 'x' * 61, 'kind': 'expense'})
    assert res.status_code == 400
    assert res.get_json()['errors']['name'] == ['required or length']
    res = client.post('/api/categories', json={'name': '  Food  ', 'kind': 'expense'})
    assert res.status_code == 201
    assert res.get_json()['data']['name'] == 'Food'
    cat_id = res.get_json()['data']['id']
    res = client.post('/api/categories', json={'name': 'fOoD ', 'kind': 'expense'})
    assert res.status_code == 409
    res = client.post('/api/categories', json={'name': 'Groceries', 'kind': 'expense'})
    assert res.status_code == 201
    cat2_id = res.get_json()['data']['id']
    res = client.put(f'/api/categories/{cat2_id}', json={'name': '  FoOd  '})
    assert res.status_code == 409
    res = client.put(f'/api/categories/{cat_id}', json={'name': '   '})
    assert res.status_code == 400
    res = client.put(f'/api/categories/{cat_id}', json={'name': 'x' * 61})
    assert res.status_code == 400
