import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseHelper:
    def __init__(self, db_path='bookstore.db'):
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'customer',
                street TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                zipcode TEXT NOT NULL,
                mailing_street TEXT,
                mailing_city TEXT,
                mailing_state TEXT,
                mailing_zipcode TEXT,
                favorite_genre TEXT
            )
        ''')

        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                isbn TEXT UNIQUE NOT NULL,
                description TEXT,
                cover_image TEXT
            )
        ''')

        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                shipping_street TEXT NOT NULL,
                shipping_city TEXT NOT NULL,
                shipping_state TEXT NOT NULL,
                shipping_zipcode TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')

        # SupplierOrders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SupplierOrders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                group_order_id INTEGER,
                status TEXT DEFAULT 'Pending',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')

        # Wishlist table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Wishlist (
                wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')

        # Insert default admin user if not exists
        cursor.execute("SELECT COUNT(*) FROM Users WHERE email = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO Users (first_name, last_name, email, password, role, street, city, state, zipcode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('Admin', 'User', 'admin', generate_password_hash('admintest'), 'admin', '123 Admin St', 'Admin City', 'AD', '12345'))

        conn.commit()
        conn.close()

    def register_user(self, first_name, email, password, last_name, street, city, state, zipcode, mailing_street=None, mailing_city=None, mailing_state=None, mailing_zipcode=None, favorite_genre=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO Users (first_name, last_name, email, password, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, email, generate_password_hash(password), street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def login_user(self, identifier, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? OR username = ?", (identifier, identifier))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            return dict(user)
        return None

    def get_user_role(self, identifier):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM Users WHERE email = ? OR username = ?", (identifier, identifier))
        result = cursor.fetchone()
        conn.close()
        return result['role'] if result else None

    def get_user_profile_by_identifier(self, identifier):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? OR username = ?", (identifier, identifier))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def update_user_profile(self, email, first_name, last_name, email_new, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE Users 
            SET first_name = ?, last_name = ?, email = ?, street = ?, city = ?, state = ?, zipcode = ?, 
                mailing_street = ?, mailing_city = ?, mailing_state = ?, mailing_zipcode = ?
            WHERE email = ?
        ''', (first_name, last_name, email_new, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, email))
        conn.commit()
        conn.close()

    def get_all_books(self, page, per_page, search_query=None, sort=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM Books"
        params = []
        
        if search_query:
            query += " WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
        
        if sort:
            if sort == 'title_asc':
                query += " ORDER BY title ASC"
            elif sort == 'title_desc':
                query += " ORDER BY title DESC"
            elif sort == 'price_asc':
                query += " ORDER BY price ASC"
            elif sort == 'price_desc':
                query += " ORDER BY price DESC"
        
        # Total count for pagination
        total_query = f"SELECT COUNT(*) FROM ({query}) AS total"
        cursor.execute(total_query, params)
        total_books = cursor.fetchone()[0]
        
        # Paginated results
        query += " LIMIT ? OFFSET ?"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        books = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return books, total_books

    def get_book_by_id(self, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books WHERE book_id = ?", (book_id,))
        book = cursor.fetchone()
        conn.close()
        return dict(book) if book else None

    def add_book(self, title, author, genre, price, quantity, isbn, description, cover_image=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cover_url = cover_image or f"http://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
        cursor.execute("INSERT INTO Books (title, author, genre, price, quantity, isbn, description, cover_image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (title, author, genre, price, quantity, isbn, description, cover_url))
        conn.commit()
        conn.close()

    def update_book_quantity(self, book_id, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Books SET quantity = ? WHERE book_id = ?", (quantity, book_id))
        conn.commit()
        conn.close()

    def remove_book(self, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Books WHERE book_id = ?", (book_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            raise ValueError("Book not found")
        cursor.execute("DELETE FROM SupplierOrders WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Orders WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Wishlist WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Books WHERE book_id = ?", (book_id,))
        conn.commit()
        conn.close()

    def add_order(self, customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM Books WHERE book_id = ?", (book_id,))
        book = cursor.fetchone()
        if not book or book['quantity'] < quantity:
            conn.close()
            return None
        cursor.execute("UPDATE Books SET quantity = quantity - ? WHERE book_id = ?", (quantity, book_id))
        cursor.execute('''
            INSERT INTO Orders (customer_email, book_id, quantity, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_email, book_id, quantity, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def get_all_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, b.title 
            FROM Orders o 
            JOIN Books b ON o.book_id = b.book_id
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def get_user_orders(self, email):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, b.title 
            FROM Orders o 
            JOIN Books b ON o.book_id = b.book_id 
            WHERE o.customer_email = ?
        ''', (email,))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def cancel_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, book_id, quantity FROM Orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()
        if order and order['status'] == 'Pending':
            cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (order['quantity'], order['book_id']))
            cursor.execute("DELETE FROM Orders WHERE order_id = ?", (order_id,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

    def add_supplier_order(self, supplier, book_id, quantity, price, group_order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO SupplierOrders (supplier, book_id, quantity, price, group_order_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (supplier, book_id, quantity, price, group_order_id))
        conn.commit()
        conn.close()

    def get_all_supplier_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT so.*, b.title 
            FROM SupplierOrders so 
            JOIN Books b ON so.book_id = b.book_id
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def complete_supplier_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, book_id, quantity FROM SupplierOrders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()
        if order and order['status'] == 'Pending':
            cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (order['quantity'], order['book_id']))
            cursor.execute("UPDATE SupplierOrders SET status = 'Completed' WHERE order_id = ?", (order_id,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

    def cancel_supplier_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM SupplierOrders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()
        if order and order['status'] == 'Pending':
            cursor.execute("DELETE FROM SupplierOrders WHERE order_id = ?", (order_id,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

    def add_to_wishlist(self, customer_email, book_id, quantity=1):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Wishlist WHERE customer_email = ? AND book_id = ?", (customer_email, book_id))
        if cursor.fetchone():
            cursor.execute("UPDATE Wishlist SET quantity = quantity + ? WHERE customer_email = ? AND book_id = ?", (quantity, customer_email, book_id))
        else:
            cursor.execute("INSERT INTO Wishlist (customer_email, book_id, quantity) VALUES (?, ?, ?)", (customer_email, book_id, quantity))
        conn.commit()
        conn.close()

    def get_user_wishlist(self, email):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Wishlist WHERE customer_email = ?", (email,))
        wishlist = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return wishlist

    def remove_from_wishlist(self, customer_email, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Wishlist WHERE customer_email = ? AND book_id = ?", (customer_email, book_id))
        conn.commit()
        conn.close()

    def get_sales_analytics(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(o.quantity * b.price) as total_sales,
                   COUNT(DISTINCT o.order_id) as total_orders
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.status = 'Completed'
        """)
        result = cursor.fetchone()
        total_sales = result[0] if result[0] is not None else 0.0
        total_orders = result[1] if result[1] is not None else 0
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0.0
        conn.close()
        return {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value
        }

    def update_supplier_order_status(self, group_order_id, status):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE SupplierOrders SET status = ? WHERE group_order_id = ?", (status, group_order_id))
        # If status is 'Processed', update book quantities
        if status == 'Processed':
            cursor.execute("SELECT book_id, quantity FROM SupplierOrders WHERE group_order_id = ?", (group_order_id,))
            books = cursor.fetchall()
            for book in books:
                cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (book['quantity'], book['book_id']))
        # If status is 'Cancelled' and still 'Pending', no inventory update needed (already handled by cancel_supplier_order if needed)
        conn.commit()
        conn.close()

if __name__ == "__main__":
    db = DatabaseHelper()
    # For testing initialization
    print("Database initialized successfully!")