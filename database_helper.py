import sqlite3
import os

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
                password TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_username TEXT NOT NULL,
                book_id INTEGER NOT NULL,
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
        count = cursor.fetchone()[0]
        return count > 0

    def _insert_sample_books(self, cursor):
        books = [
            ("The Great Gatsby", "F. Scott Fitzgerald", "Classic", 10.99),
            ("To Kill a Mockingbird", "Harper Lee", "Classic", 8.99),
            ("1984", "George Orwell", "Dystopian", 9.99),
            ("Pride and Prejudice", "Jane Austen", "Romance", 7.99),
            ("Moby-Dick", "Herman Melville", "Adventure", 11.49),
            ("War and Peace", "Leo Tolstoy", "Historical", 12.99),
            ("The Catcher in the Rye", "J.D. Salinger", "Coming-of-age", 9.49),
            ("Brave New World", "Aldous Huxley", "Dystopian", 10.49),
            ("Crime and Punishment", "Fyodor Dostoevsky", "Psychological", 8.99),
        ]
        cursor.executemany("INSERT INTO Books (title, author, genre, price) VALUES (?, ?, ?, ?)", books)
        print("Sample books added to database!")

    def get_all_books(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books ORDER BY title")
        rows = cursor.fetchall()
        books = [{"book_id": row[0], "title": row[1], "author": row[2], "genre": row[3], "price": row[4]} for row in rows]
        conn.close()
        return books

    def login_user(self, username, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def register_user(self, first_name, last_name, username, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Users (first_name, last_name, username, password) VALUES (?, ?, ?, ?)",
                          (first_name, last_name, username, password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_order(self, customer_username, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Orders (customer_username, book_id, status) VALUES (?, ?, 'Pending')",
                      (customer_username, book_id))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def cancel_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM Orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None  # Order not found
        if result[0] != 'Pending':
            conn.close()
            return False  # Cannot cancel non-pending order
        cursor.execute("UPDATE Orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
        conn.commit()
        conn.close()
        return True  # Order cancelled

    def get_user_orders(self, username):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.order_id, b.title, b.author, o.status
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.customer_username = ?
        """, (username,))
        rows = cursor.fetchall()
        orders = [{"order_id": row[0], "title": row[1], "author": row[2], "status": row[3]} for row in rows]
        conn.close()
        return orders