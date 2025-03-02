from flask import render_template, request, redirect, url_for, flash, jsonify, session
from database_helper import DatabaseHelper

db_helper = DatabaseHelper()

def register_routes(app):
    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            if db_helper.login_user(username, password):
                session['username'] = username
                flash("✅ Login successful!", "success")
                return redirect(url_for("bookstore"))
            else:
                flash("❌ Invalid credentials!", "error")
        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            username = request.form["username"]
            password = request.form["password"]
            if db_helper.register_user(first_name, last_name, username, password):
                flash("✅ Signup successful! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                flash("❌ Signup failed! Username may already exist.", "error")
        return render_template("signup.html")

    @app.route("/bookstore", methods=["GET", "POST"])
    def bookstore():
        if 'username' not in session:
            flash("❌ Please log in to access the bookstore.", "error")
            return redirect(url_for("login"))
        books = []
        orders = db_helper.get_user_orders(session['username'])
        if request.method == "POST":
            if "search_books" in request.form:
                search_query = request.form["search"].lower()
                all_books = db_helper.get_all_books()
                books = [book for book in all_books if search_query in book["title"].lower() or 
                         search_query in book["author"].lower() or search_query in book["genre"].lower()]
            elif "browse" in request.form:
                books = db_helper.get_all_books()
        return render_template("bookstore.html", books=books, orders=orders)

    @app.route("/cart", methods=["GET", "POST"])
    def cart():
        if 'username' not in session:
            flash("❌ Please log in to access the cart.", "error")
            return redirect(url_for("login"))
        cart = session.get('cart', [])
        books = [book for book in db_helper.get_all_books() if book["book_id"] in cart]
        if request.method == "POST" and "checkout" in request.form:
            for book_id in cart:
                db_helper.add_order(session['username'], book_id)
            session['cart'] = []
            flash("✅ Order placed for cart items!", "success")
            return redirect(url_for("bookstore"))
        return render_template("cart.html", books=books)

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if 'username' not in session:
            flash("❌ Please log in to access your profile.", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            address = request.form["address"]
            db_helper.update_address(session['username'], address)
            flash("✅ Address updated!", "success")
        return render_template("profile.html")

    @app.route("/admin/add_book", methods=["GET", "POST"])
    def admin_add_book():
        if 'username' not in session or session['username'] != 'admin':
            flash("❌ Admin access only!", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            title = request.form["title"]
            author = request.form["author"]
            genre = request.form["genre"]
            price = float(request.form["price"])
            db_helper.add_book(title, author, genre, price)
            flash("✅ Book added!", "success")
            return redirect(url_for("bookstore"))
        return render_template("admin_add_book.html")

    @app.route("/admin/inventory")
    def admin_inventory():
        if 'username' not in session or session['username'] != 'admin':
            flash("❌ Admin access only!", "error")
            return redirect(url_for("login"))
        books = db_helper.get_all_books()
        return render_template("admin_inventory.html", books=books)

    @app.route("/add_to_cart", methods=["POST"])
    def add_to_cart():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = int(request.form.get("book_id"))
        cart = session.get('cart', [])
        if book_id not in cart:
            cart.append(book_id)
            session['cart'] = cart
        return jsonify({'message': 'Book added to cart'}), 200

    @app.route("/orders", methods=["POST"])
    def create_order():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = request.form.get("book_id")
        if not book_id:
            return jsonify({'error': 'Book ID required'}), 400
        order_id = db_helper.add_order(session['username'], int(book_id))
        return jsonify({'message': 'Order created', 'order_id': order_id}), 201

    @app.route("/orders/<int:order_id>/cancel", methods=["POST"])
    def cancel_order(order_id):
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        result = db_helper.cancel_order(order_id)
        if result is None:
            return jsonify({'error': 'Order not found'}), 404
        if not result:
            return jsonify({'error': 'Cannot cancel processed order'}), 400
        return jsonify({'message': 'Order cancelled', 'order_id': order_id}), 200