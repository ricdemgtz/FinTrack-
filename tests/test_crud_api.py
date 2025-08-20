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

def test_cruds(client):
    register(client)
    # Accounts
    res = client.post(
        '/api/accounts',
        json={'name': 'Cash', 'type': 'cash', 'opening_balance': 100, 'active': False},
    )
    assert res.status_code == 201
    acc_id = res.get_json()['data']['id']
    assert res.get_json()['data']['opening_balance'] == 100
    assert res.get_json()['data']['active'] is False
    res = client.get('/api/accounts')
    assert len(res.get_json()['data']) == 1
    res = client.put(f'/api/accounts/{acc_id}', json={'name': 'Wallet', 'active': True})
    assert res.get_json()['data']['name'] == 'Wallet'
    assert res.get_json()['data']['active'] is True
    res = client.put(f'/api/accounts/{acc_id}', json={'active': False})
    assert res.get_json()['data']['active'] is False
    res = client.delete(f'/api/accounts/{acc_id}')
    assert res.get_json()['success'] is True
    assert client.get('/api/accounts').get_json()['data'] == []
    res = client.post(f'/api/accounts/{acc_id}/restore', json={})
    assert res.get_json()['data']['active'] is False
    assert res.get_json()['data']['opening_balance'] == 100
    res = client.delete(f'/api/accounts/{acc_id}')
    client.post(f'/api/accounts/{acc_id}/restore', json={'active': True})
    assert client.get(f'/api/accounts/{acc_id}').get_json()['data']['active'] is True

    # Categories
    res = client.post('/api/categories', json={'name': 'Food', 'kind': 'expense'})
    assert res.status_code == 201
    cat_id = res.get_json()['data']['id']
    res = client.get('/api/categories')
    assert len(res.get_json()['data']) == 1
    res = client.put(f'/api/categories/{cat_id}', json={'color': '#ff0000'})
    assert res.get_json()['data']['color'] == '#FF0000'
    res = client.delete(f'/api/categories/{cat_id}')
    assert res.status_code == 400
    res = client.delete(f'/api/categories/{cat_id}?confirm=true')
    assert res.get_json()['success'] is True
    assert client.get('/api/categories').get_json()['data'] == []
    res = client.post(f'/api/categories/{cat_id}/restore')
    assert res.get_json()['data']['id'] == cat_id

    # Category parent-child and extra fields
    res = client.post(
        '/api/categories',
        json={'name': 'Bills', 'kind': 'expense', 'icon_emoji': '\U0001F4A1'},
    )
    parent_id = res.get_json()['data']['id']
    res = client.post(
        '/api/categories',
        json={'name': 'Electricity', 'kind': 'expense', 'parent_id': parent_id},
    )
    child_id = res.get_json()['data']['id']
    res = client.get(f'/api/categories/{child_id}')
    data = res.get_json()['data']
    assert data['parent_id'] == parent_id
    assert data['icon_emoji'] is None
    assert data['is_system'] is False
    res = client.put(f'/api/categories/{child_id}', json={'icon_emoji': '\u26A1'})
    updated = res.get_json()['data']
    assert updated['icon_emoji'] == '\u26A1'
    res = client.put(f'/api/categories/{child_id}', json={'is_system': True})
    assert res.status_code == 400
    assert client.get(f'/api/categories/{child_id}').get_json()['data']['is_system'] is False

    # System categories cannot be deleted
    res = client.post('/api/categories', json={'name': 'SysCat', 'kind': 'expense', 'is_system': True})
    sys_id = res.get_json()['data']['id']
    res = client.delete(f'/api/categories/{sys_id}?confirm=true')
    assert res.status_code == 400

    # Prevent cycles in category hierarchy
    res = client.put(f'/api/categories/{parent_id}', json={'parent_id': child_id})
    assert res.status_code == 400

    res = client.post(
        '/api/categories',
        json={'name': 'Bad', 'kind': 'expense', 'icon_emoji': 'abc'},
    )
    assert res.status_code == 422
    res = client.put(
        f'/api/categories/{child_id}',
        json={'icon_emoji': '👨‍👩‍👦'},
    )
    assert res.status_code == 422

    # Rules
    res = client.post('/api/rules', json={'pattern': 'Star', 'category_id': cat_id})
    assert res.status_code == 201
    rule_id = res.get_json()['data']['id']
    res = client.get('/api/rules')
    assert len(res.get_json()['data']) == 1
    res = client.put(f'/api/rules/{rule_id}', json={'active': False})
    assert res.get_json()['data']['active'] is False
    res = client.delete(f'/api/rules/{rule_id}')
    assert res.get_json()['success'] is True
    assert client.get('/api/rules').get_json()['data'] == []
    res = client.post(f'/api/rules/{rule_id}/restore')
    assert res.get_json()['data']['id'] == rule_id

    # Account delete disables scoped rules
    res = client.post('/api/rules', json={'pattern': 'Scoped', 'scope_account_id': acc_id})
    scoped_rule_id = res.get_json()['data']['id']
    res = client.delete(f'/api/accounts/{acc_id}')
    data = res.get_json()
    assert data['success'] is True
    assert data['message'] == '1 rule(s) disabled'
    assert data['data']['disabled_rules'] == 1
    res = client.get(f'/api/rules/{scoped_rule_id}')
    assert res.get_json()['data']['active'] is False

    # Parent category must belong to the same user
    client.post('/auth/logout', follow_redirects=True)
    client.post(
        '/auth/register',
        data={'email': 'other@example.com', 'password': 'pass'},
        follow_redirects=True,
    )
    res = client.post(
        '/api/categories',
        json={'name': 'Other', 'kind': 'expense', 'parent_id': parent_id},
    )
    assert res.status_code == 400
