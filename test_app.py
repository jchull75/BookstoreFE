import pytest
from app import app
from database_helper import DatabaseHelper

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db():
    db = DatabaseHelper()
    conn = db._get_connection()
    conn.execute("DELETE FROM Users")
    conn.execute("DELETE FROM Orders")
    conn.execute("DELETE FROM Books")
    conn.commit()
    conn.close()
    return db

def test_login_page(client):
    rv = client.get('/')
    assert b"Login" in rv.data

def test_signup(client, db):
    rv = client.post('/signup', data={
        'first_name': 'Test', 'last_name': 'User', 'username': 'testuser', 'password': 'testpass'
    })
    assert rv.status_code == 302  # Redirect to login

def test_login_success(client, db):
    db.register_user('Test', 'User', 'testuser', 'testpass')
    rv = client.post('/', data={'username': 'testuser', 'password': 'testpass'})
    assert rv.status_code == 302  # Redirect to bookstore

def test_bookstore_unauthenticated(client):
    rv = client.get('/bookstore')
    assert b"Please log in" in rv.data

def test_add_to_cart(client, db):
    db.register_user('Test', 'User', 'testuser', 'testpass')
    client.post('/', data={'username': 'testuser', 'password': 'testpass'})
    db.add_book("Test Book", "Test Author", "Test Genre", 9.99)
    rv = client.post('/add_to_cart', data={'book_id': '1'})
    assert b"Book added to cart" in rv.data

def test_admin_add_book(client, db):
    db.register_user('Admin', 'User', 'admin', 'adminpass')
    client.post('/', data={'username': 'admin', 'password': 'adminpass'})
    rv = client.post('/admin/add_book', data={
        'title': 'New Book', 'author': 'New Author', 'genre': 'New Genre', 'price': '5.99'
    })
    assert rv.status_code == 302  # Redirect to bookstore

def test_admin_inventory(client, db):
    db.register_user('Admin', 'User', 'admin', 'adminpass')
    client.post('/', data={'username': 'admin', 'password': 'adminpass'})
    db.add_book("Test Book", "Test Author", "Test Genre", 9.99)
    rv = client.get('/admin/inventory')
    assert b"Test Book" in rv.data