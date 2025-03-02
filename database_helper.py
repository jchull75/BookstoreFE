import sqlite3
import os
from hashlib import sha256

DATABASE_NAME = "bookstore.db"

class DatabaseHelper:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), DATABASE_NAME)
        self._initialize_database()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _initialize_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                address TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_username TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'Pending',
                FOREIGN KEY (customer_username) REFERENCES Users(username),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        """)

        if not self._has_books(cursor):
            self._insert_sample_books(cursor)

        conn.commit()
        conn.close()

    def _has_books(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM Books")
        return cursor.fetchone()[0] > 0

    def _insert_sample_books(self, cursor):
        books = [
            ("The Great Gatsby", "F. Scott Fitzgerald", "Classic", 10.99, 5),
            ("To Kill a Mockingbird", "Harper Lee", "Classic", 8.99, 3),
            ("1984", "George Orwell", "Dystopian", 9.99, 7),
            ("Pride and Prejudice", "Jane Austen", "Romance", 7.99, 4),
            ("Moby-Dick", "Herman Melville", "Adventure", 11.49, 2),
            ("War and Peace", "Leo Tolstoy", "Historical", 12.99, 1),
            ("The Catcher in the Rye", "J.D. Salinger", "Coming-of-age", 9.49, 6),
            ("Brave New World", "Aldous Huxley", "Dystopian", 10.49, 3),
            ("Crime and Punishment", "Fyodor Dostoevsky", "Psychological", 8.99, 5),
        ]
        cursor.executemany("INSERT INTO Books (title, author, genre, price, quantity) VALUES (?, ?, ?, ?, ?)", books)
        print("Sample books added to database!")

    def get_all_books(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books ORDER BY title")
        rows = cursor.fetchall()
        books = [{"book_id": row[0], "title": row[1], "author": row[2], "genre": row[3], "price": row[4], "quantity": row[5]} for row in rows]
        conn.close()
        return books

    def search_books(self, query):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books WHERE title LIKE ? OR author LIKE ? ORDER BY title", (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        books = [{"book_id": row[0], "title": row[1], "author": row[2], "genre": row[3], "price": row[4], "quantity": row[5]} for row in rows]
        conn.close()
        return books

    def login_user(self, username, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", (username, hashed_password))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def register_user(self, first_name, last_name, username, password, address=""):
        conn = self._get_connection()
        cursor = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()
        try:
            cursor.execute("INSERT INTO Users (first_name, last_name, username, password, address) VALUES (?, ?, ?, ?, ?)",
                          (first_name, last_name, username, hashed_password, address))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_user_address(self, username):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT address FROM Users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else ""

    def update_user_address(self, username, address):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET address = ? WHERE username = ?", (address, username))
        conn.commit()
        conn.close()

    def add_order(self, customer_username, book_id, quantity=1):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM Books WHERE book_id = ?", (book_id,))
        stock = cursor.fetchone()[0]
        if stock < quantity:
            conn.close()
            return None
        cursor.execute("UPDATE Books SET quantity = quantity - ? WHERE book_id = ?", (quantity, book_id))
        cursor.execute("INSERT INTO Orders (customer_username, book_id, quantity, status) VALUES (?, ?, ?, 'Pending')",
                      (customer_username, book_id, quantity))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def cancel_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, book_id, quantity FROM Orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        if not result or result[0] != 'Pending':
            conn.close()
            return False
        cursor.execute("UPDATE Orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
        cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (result[2], result[1]))
        conn.commit()
        conn.close()
        return True

    def get_user_orders(self, username):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.order_id, b.title, b.author, o.status, o.quantity, b.price
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.customer_username = ?
        """, (username,))
        rows = cursor.fetchall()
        orders = [{"order_id": row[0], "title": row[1], "author": row[2], "status": row[3], "quantity": row[4], "price": row[5]} for row in rows]
        conn.close()
        return orders

    def add_book(self, title, author, genre, price, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Books (title, author, genre, price, quantity) VALUES (?, ?, ?, ?, ?)",
                      (title, author, genre, price, quantity))
        conn.commit()
        conn.close()

    def get_inventory(self):
        return self.get_all_books()