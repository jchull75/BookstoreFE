import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
                street TEXT,
                city TEXT,
                state TEXT,
                zipcode TEXT
            )
        """)

        for column in ["street", "city", "state", "zipcode"]:
            try:
                cursor.execute(f"ALTER TABLE Users ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                isbn TEXT
            )
        """)

        try:
            cursor.execute("ALTER TABLE Books ADD COLUMN isbn TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_username TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                shipping_street TEXT,
                shipping_city TEXT,
                shipping_state TEXT,
                shipping_zipcode TEXT,
                payment_method TEXT,
                payment_status TEXT DEFAULT 'Pending',
                FOREIGN KEY (customer_username) REFERENCES Users(username),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        """)

        for column in ["shipping_street", "shipping_city", "shipping_state", "shipping_zipcode", "payment_method", "payment_status"]:
            try:
                cursor.execute(f"ALTER TABLE Orders ADD COLUMN {column} {'TEXT' if column != 'payment_status' else 'TEXT DEFAULT \"Pending\"'}")
            except sqlite3.OperationalError:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS InventoryOrders (
                inventory_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
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
            ("The Great Gatsby", "F. Scott Fitzgerald", "Classic Fiction", 10.99, 10, "0743273567"),
            ("1984", "George Orwell", "Dystopian", 9.99, 10, "0451524934"),
            ("To Kill a Mockingbird", "Harper Lee", "Historical Fiction", 12.99, 10, "0446310786"),
            ("The Catcher in the Rye", "J.D. Salinger", "Fiction", 8.99, 10, "0316769487"),
            ("Moby-Dick", "Herman Melville", "Adventure", 11.49, 10, "0142437247"),
            ("Pride and Prejudice", "Jane Austen", "Romance", 7.99, 10, "0141439513"),
            ("The Hobbit", "J.R.R. Tolkien", "Fantasy", 14.99, 10, "0345339681"),
            ("Harry Potter and the Sorcerer’s Stone", "J.K. Rowling", "Fantasy", 12.49, 10, "059035342X"),
            ("The Da Vinci Code", "Dan Brown", "Thriller", 10.99, 10, "0307474275"),
            ("The Alchemist", "Paulo Coelho", "Philosophical", 9.99, 10, "0062315005"),
            ("The Foxhole Court", "Nora Sakavic", "Sports Fiction/Drama", 11.99, 10, "1482697521"),
            ("The Night Circus", "Erin Morgenstern", "Fantasy/Romance", 15.99, 10, "0307744434"),
            ("Project Hail Mary", "Andy Weir", "Science Fiction", 16.49, 10, "0593135202"),
            ("The Very Secret Society of Irregular Witches", "Sangu Mandanna", "Cozy Fantasy", 13.99, 10, "0593209869"),
            ("The Silent Patient", "Alex Michaelides", "Psychological Thriller", 14.99, 10, "1250301696"),
            ("Braiding Sweetgrass", "Robin Wall Kimmerer", "Nonfiction/Nature", 12.99, 10, "1571313567"),
            ("A Man Called Ove", "Fredrik Backman", "Contemporary Fiction", 11.49, 10, "1476738025"),
            ("The House in the Cerulean Sea", "TJ Klune", "Fantasy/Feel-Good", 14.49, 10, "1250217288"),
            ("Mexican Gothic", "Silvia Moreno-Garcia", "Gothic Horror", 13.99, 10, "0525620788"),
            ("Tomorrow, and Tomorrow, and Tomorrow", "Gabrielle Zevin", "Literary Coming-of-Age", 15.99, 10, "0593321200"),
            ("Dune", "Frank Herbert", "Science Fiction", 15.99, 10, "0441172717"),
            ("The Shining", "Stephen King", "Horror", 11.99, 10, "0307743659"),
            ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "Non-Fiction", 18.49, 10, "0062316095"),
            ("The Name of the Wind", "Patrick Rothfuss", "Fantasy", 13.99, 10, "075640407X"),
            ("Gone Girl", "Gillian Flynn", "Thriller", 10.49, 10, "030758836X"),
            ("Educated", "Tara Westover", "Memoir", 14.49, 10, "0399590501"),
            ("The Martian", "Andy Weir", "Science Fiction", 12.99, 10, "0553418025"),
            ("A Game of Thrones", "George R.R. Martin", "Fantasy", 16.99, 10, "0553103547"),
            ("The Girl with the Dragon Tattoo", "Stieg Larsson", "Mystery", 11.49, 10, "0307269752"),
            ("Atomic Habits", "James Clear", "Self-Help", 15.49, 10, "0735211299"),
        ]
        cursor.executemany("INSERT INTO Books (title, author, genre, price, quantity, isbn) VALUES (?, ?, ?, ?, ?, ?)", books)
        print("Inserted 30 sample books with initial quantity of 10 into the database!")

    def get_all_books(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books ORDER BY title")
        rows = cursor.fetchall()
        books = [{"book_id": row[0], "title": row[1], "author": row[2], "genre": row[3], "price": row[4], "quantity": row[5], "isbn": row[6]} for row in rows]
        conn.close()
        return books

    def login_user(self, username, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM Users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result and check_password_hash(result[0], password)

    def register_user(self, first_name, last_name, username, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Users (first_name, last_name, username, password) VALUES (?, ?, ?, ?)",
                          (first_name, last_name, username, generate_password_hash(password)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_book(self, title, author, genre, price, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Books (title, author, genre, price, quantity) VALUES (?, ?, ?, ?, ?)",
                      (title, author, genre, price, quantity))
        conn.commit()
        conn.close()

    def add_order(self, customer_username, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM Books WHERE book_id = ?", (book_id,))
        result = cursor.fetchone()
        if not result or result[0] <= 0:
            conn.close()
            return None
        cursor.execute("UPDATE Books SET quantity = quantity - 1 WHERE book_id = ?", (book_id,))
        cursor.execute("""
            INSERT INTO Orders (customer_username, book_id, status, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, payment_status) 
            VALUES (?, ?, 'Pending', ?, ?, ?, ?, ?, 'Completed')
        """, (customer_username, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method))
        order_id = cursor.lastrowid
        cursor.execute("INSERT INTO InventoryOrders (book_id, amount, status) VALUES (?, ?, 'Pending')", (book_id, 5))
        conn.commit()
        conn.close()
        return order_id

    def cancel_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, book_id FROM Orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        if result[0] != 'Pending':
            conn.close()
            return False
        cursor.execute("UPDATE Orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
        cursor.execute("UPDATE Books SET quantity = quantity + 1 WHERE book_id = ?", (result[1],))
        conn.commit()
        conn.close()
        return True

    def get_user_orders(self, username):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.order_id, b.title, b.author, o.status, o.shipping_street, o.shipping_city, o.shipping_state, o.shipping_zipcode, o.payment_method, o.payment_status
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.customer_username = ?
        """, (username,))
        rows = cursor.fetchall()
        orders = [{"order_id": row[0], "title": row[1], "author": row[2], "status": row[3],
                  "shipping_street": row[4], "shipping_city": row[5], "shipping_state": row[6], "shipping_zipcode": row[7],
                  "payment_method": row[8], "payment_status": row[9]} for row in rows]
        conn.close()
        return orders

    def update_address(self, username, street, city, state, zipcode):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET street = ?, city = ?, state = ?, zipcode = ? WHERE username = ?",
                      (street, city, state, zipcode, username))
        conn.commit()
        conn.close()

    def get_user_address(self, username):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT street, city, state, zipcode FROM Users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"street": result[0], "city": result[1], "state": result[2], "zipcode": result[3]}
        return {"street": None, "city": None, "state": None, "zipcode": None}

    def update_book_quantity(self, book_id, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Books SET quantity = ? WHERE book_id = ?", (quantity, book_id))
        conn.commit()
        conn.close()

    def replenish_book_inventory(self, book_id, amount):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (amount, book_id))
        conn.commit()
        conn.close()

    def get_pending_inventory_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT io.inventory_order_id, b.book_id, b.title, b.author, b.genre, b.price, b.quantity, io.amount
            FROM InventoryOrders io
            JOIN Books b ON io.book_id = b.book_id
            WHERE io.status = 'Pending'
        """)
        rows = cursor.fetchall()
        orders = [{"inventory_order_id": row[0], "book_id": row[1], "title": row[2], "author": row[3], "genre": row[4], 
                  "price": row[5], "quantity": row[6], "amount": row[7]} for row in rows]
        conn.close()
        return orders

    def complete_inventory_order(self, inventory_order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT book_id, amount FROM InventoryOrders WHERE inventory_order_id = ?", (inventory_order_id,))
        result = cursor.fetchone()
        if result:
            book_id, amount = result
            cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (amount, book_id))
            cursor.execute("UPDATE InventoryOrders SET status = 'Completed' WHERE inventory_order_id = ?", (inventory_order_id,))
        conn.commit()
        conn.close()

    def get_all_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.order_id, o.customer_username, b.title, b.author, o.status, o.shipping_street, o.shipping_city, 
                   o.shipping_state, o.shipping_zipcode, o.payment_method, o.payment_status, b.price
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            ORDER BY o.order_id DESC
        """)
        rows = cursor.fetchall()
        orders = [{"order_id": row[0], "customer_username": row[1], "title": row[2], "author": row[3], "status": row[4],
                  "shipping_street": row[5], "shipping_city": row[6], "shipping_state": row[7], "shipping_zipcode": row[8],
                  "payment_method": row[9], "payment_status": row[10], "price": row[11]} for row in rows]
        conn.close()
        return orders

    def get_sales_analytics(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.book_id, b.title, b.author, COUNT(o.order_id) as order_count
            FROM Books b
            LEFT JOIN Orders o ON b.book_id = o.book_id
            GROUP BY b.book_id, b.title, b.author
            ORDER BY order_count DESC
            LIMIT 5
        """)
        top_books = [{"book_id": row[0], "title": row[1], "author": row[2], "order_count": row[3]} for row in cursor.fetchall()]
        cursor.execute("""
            SELECT SUM(b.price) as total_sales
            FROM Orders o
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.payment_status = 'Completed'
        """)
        total_sales = cursor.fetchone()[0] or 0.0
        conn.close()
        return {"top_books": top_books, "total_sales": total_sales}