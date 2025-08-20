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


def test_category_color_validation(client):
    register(client)
    # Invalid color on create
    res = client.post('/api/categories', json={'name': 'Bad', 'kind': 'expense', 'color': '#123'})
    assert res.status_code == 422
    assert res.get_json()['errors']['color'] == ['invalid hex']

    # Valid color without # and lowercase
    res = client.post('/api/categories', json={'name': 'Food', 'kind': 'expense', 'color': 'ff00ff'})
    assert res.status_code == 201
    cat = res.get_json()['data']
    assert cat['color'] == '#FF00FF'
    cat_id = cat['id']

    # Update with mixed-case and leading #
    res = client.put(f'/api/categories/{cat_id}', json={'color': '#00ff00'})
    assert res.status_code == 200
    assert res.get_json()['data']['color'] == '#00FF00'

    # Invalid color on update
    res = client.put(f'/api/categories/{cat_id}', json={'color': 'xyz'})
    assert res.status_code == 422
    assert res.get_json()['errors']['color'] == ['invalid hex']
