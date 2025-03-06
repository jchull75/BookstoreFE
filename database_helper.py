import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DatabaseHelper:
    def __init__(self, db_path="bookstore.db"):
        self.db_path = db_path
        # Allow multiple threads to use the same connection
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.setup_database()

    def setup_database(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS Users (
                    email TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    street TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    zipcode TEXT NOT NULL,
                    mailing_street TEXT,
                    mailing_city TEXT,
                    mailing_state TEXT,
                    mailing_zipcode TEXT
                );
                CREATE TABLE IF NOT EXISTS Books (
                    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    isbn TEXT,
                    description TEXT,
                    cover_image TEXT
                );
                CREATE TABLE IF NOT EXISTS Reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    customer_email TEXT,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT,
                    review_date TEXT,
                    FOREIGN KEY (book_id) REFERENCES Books(book_id),
                    FOREIGN KEY (customer_email) REFERENCES Users(email)
                );
                CREATE TABLE IF NOT EXISTS Orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_email TEXT,
                    book_id INTEGER,
                    shipping_street TEXT,
                    shipping_city TEXT,
                    shipping_state TEXT,
                    shipping_zipcode TEXT,
                    payment_method TEXT,
                    quantity INTEGER,
                    payment_details TEXT,
                    status TEXT DEFAULT 'Pending',
                    order_date TEXT,
                    FOREIGN KEY (customer_email) REFERENCES Users(email),
                    FOREIGN KEY (book_id) REFERENCES Books(book_id)
                );
                CREATE TABLE IF NOT EXISTS SupplierOrders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier TEXT,
                    book_id INTEGER,
                    quantity INTEGER,
                    price REAL,
                    group_order_id INTEGER,
                    status TEXT DEFAULT 'Pending',
                    order_date TEXT,
                    FOREIGN KEY (book_id) REFERENCES Books(book_id)
                );
                CREATE TABLE IF NOT EXISTS Wishlist (
                    customer_email TEXT,
                    book_id INTEGER,
                    quantity INTEGER,
                    PRIMARY KEY (customer_email, book_id),
                    FOREIGN KEY (customer_email) REFERENCES Users(email),
                    FOREIGN KEY (book_id) REFERENCES Books(book_id)
                );
            """)
            self.conn.commit()

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def register_user(self, first_name, email, password, last_name, street, city, state, zipcode):
        with self.conn:
            cursor = self.conn.cursor()
            try:
                cursor.execute("INSERT INTO Users (email, password, first_name, last_name, street, city, state, zipcode) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (email, password, first_name, last_name, street, city, state, zipcode))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def login_user(self, identifier, password):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?", (identifier, password))
            return cursor.fetchone()

    def get_user_profile_by_identifier(self, identifier):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE email = ?", (identifier,))
            return dict(cursor.fetchone()) if cursor.fetchone() else None

    def update_user_profile(self, email, first_name, last_name, new_email, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE Users SET email = ?, first_name = ?, last_name = ?, street = ?, city = ?, state = ?, zipcode = ?, 
                mailing_street = ?, mailing_city = ?, mailing_state = ?, mailing_zipcode = ? WHERE email = ?
            """, (new_email, first_name, last_name, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, email))
            self.conn.commit()

    def get_all_books(self, page, per_page):
        with self.conn:
            cursor = self.conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute("SELECT * FROM Books LIMIT ? OFFSET ?", (per_page, offset))
            books = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM Books")
            total_books = cursor.fetchone()[0]
            return books, total_books

    def get_book_by_id(self, book_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM Books WHERE book_id = ?", (book_id,))
            return dict(cursor.fetchone()) if cursor.fetchone() else None

    def get_reviews_for_book(self, book_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT r.*, u.first_name, u.last_name 
                FROM Reviews r 
                JOIN Users u ON r.customer_email = u.email 
                WHERE r.book_id = ? 
                ORDER BY r.review_date DESC
            """, (book_id,))
            return [dict(row) for row in cursor.fetchall()]

    def add_book(self, title, author, genre, price, quantity, isbn, description):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO Books (title, author, genre, price, quantity, isbn, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (title, author, genre, price, quantity, isbn, description))
            self.conn.commit()

    def update_book_quantity(self, book_id, quantity):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE Books SET quantity = ? WHERE book_id = ?", (quantity, book_id))
            self.conn.commit()

    def remove_book(self, book_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM Books WHERE book_id = ?", (book_id,))
            self.conn.commit()

    def add_order(self, customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, quantity, payment_details=None):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT quantity FROM Books WHERE book_id = ?", (book_id,))
            available = cursor.fetchone()[0]
            if available < quantity:
                return None
            cursor.execute("UPDATE Books SET quantity = quantity - ? WHERE book_id = ?", (quantity, book_id))
            cursor.execute("""
                INSERT INTO Orders (customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, quantity, payment_details, order_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, quantity, str(payment_details) if payment_details else None, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit()
            cursor.execute("SELECT last_insert_rowid()")
            return cursor.fetchone()[0]

    def get_user_orders(self, customer_email):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT o.order_id, b.title, o.quantity, b.price, o.payment_method, o.payment_details, o.shipping_street, o.shipping_city, o.shipping_state, o.shipping_zipcode, o.status, o.order_date
                FROM Orders o 
                JOIN Books b ON o.book_id = b.book_id 
                WHERE o.customer_email = ?
            """, (customer_email,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_orders(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT o.order_id, b.title, o.quantity, b.price, o.payment_method, o.payment_details, o.shipping_street, o.shipping_city, o.shipping_state, o.shipping_zipcode, o.status, o.order_date
                FROM Orders o 
                JOIN Books b ON o.book_id = b.book_id
            """)
            return [dict(row) for row in cursor.fetchall()]

    def cancel_order(self, order_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT status FROM Orders WHERE order_id = ?", (order_id,))
            status = cursor.fetchone()
            if not status or status[0] not in ['Pending', 'Shipped']:
                return False
            cursor.execute("UPDATE Orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
            self.conn.commit()
            return True

    def add_supplier_order(self, supplier, book_id, quantity, price, group_order_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO SupplierOrders (supplier, book_id, quantity, price, group_order_id, order_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (supplier, book_id, quantity, price, group_order_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit()

    def get_all_supplier_orders(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM SupplierOrders")
            return [dict(row) for row in cursor.fetchall()]

    def update_supplier_order_status(self, group_order_id, status):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE SupplierOrders SET status = ? WHERE group_order_id = ?", (status, group_order_id))
            self.conn.commit()

    def get_user_wishlist(self, customer_email):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT w.book_id, b.title, b.author, b.price, w.quantity
                FROM Wishlist w
                JOIN Books b ON w.book_id = b.book_id
                WHERE w.customer_email = ?
            """, (customer_email,))
            return [dict(row) for row in cursor.fetchall()]

    def add_to_wishlist(self, customer_email, book_id, quantity):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO Wishlist (customer_email, book_id, quantity) VALUES (?, ?, ?)",
                           (customer_email, book_id, quantity))
            self.conn.commit()

    def remove_from_wishlist(self, customer_email, book_id):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM Wishlist WHERE customer_email = ? AND book_id = ?", (customer_email, book_id))
            self.conn.commit()