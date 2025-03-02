from flask import render_template, request, redirect, url_for, flash, jsonify, session
from database_helper import DatabaseHelper

db_helper = DatabaseHelper()

def register_routes(app):
    def is_admin(username):
        return username == "admin"  # Simple admin check; enhance later

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
            address = request.form.get("address", "")
            if db_helper.register_user(first_name, last_name, username, password, address):
                flash("✅ Signup successful! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                flash("❌ Signup failed! Username may exist.", "error")
        return render_template("signup.html")

    @app.route("/bookstore", methods=["GET", "POST"])
    def bookstore():
        if 'username' not in session:
            flash("❌ Please log in.", "error")
            return redirect(url_for("login"))
        books = []
        cart = session.get('cart', {})
        orders = db_helper.get_user_orders(session['username'])
        if request.method == "POST":
            if "browse" in request.form:
                books = db_helper.get_all_books()
            elif "search" in request.form:
                query = request.form["query"]
                books = db_helper.search_books(query)
            elif "add_to_cart" in request.form:
                book_id = request.form["book_id"]
                quantity = int(request.form.get("quantity", 1))
                cart[book_id] = cart.get(book_id, 0) + quantity
                session['cart'] = cart
                flash("✅ Book added to cart!", "success")
        return render_template("bookstore.html", books=books, orders=orders, cart=cart)

    @app.route("/cart", methods=["GET", "POST"])
    def cart():
        if 'username' not in session:
            return redirect(url_for("login"))
        cart = session.get('cart', {})
        books = db_helper.get_all_books()
        cart_items = {book["book_id"]: book | {"quantity": cart[str(book["book_id"])]} for book in books if str(book["book_id"]) in cart}
        total = sum(item["price"] * item["quantity"] for item in cart_items.values())
        address = db_helper.get_user_address(session['username'])
        if request.method == "POST":
            if "update_address" in request.form:
                address = request.form["address"]
                db_helper.update_user_address(session['username'], address)
                flash("✅ Address updated!", "success")
            elif "checkout" in request.form:
                for book_id, item in cart_items.items():
                    order_id = db_helper.add_order(session['username'], book_id, item["quantity"])
                    if not order_id:
                        flash(f"❌ Not enough stock for {item['title']}", "error")
                        return redirect(url_for("cart"))
                session['cart'] = {}
                flash("✅ Order placed!", "success")
                return redirect(url_for("bookstore"))
        return render_template("cart.html", cart_items=cart_items, total=total, address=address)

    @app.route("/orders/<int:order_id>/cancel", methods=["POST"])
    def cancel_order(order_id):
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        result = db_helper.cancel_order(order_id)
        if not result:
            return jsonify({'error': 'Cannot cancel'}), 400
        return jsonify({'message': 'Order cancelled', 'order_id': order_id}), 200

    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if 'username' not in session or not is_admin(session['username']):
            flash("❌ Admin access only.", "error")
            return redirect(url_for("login"))
        inventory = db_helper.get_inventory()
        if request.method == "POST" and "add_book" in request.form:
            title = request.form["title"]
            author = request.form["author"]
            genre = request.form["genre"]
            price = float(request.form["price"])
            quantity = int(request.form["quantity"])
            db_helper.add_book(title, author, genre, price, quantity)
            flash("✅ Book added!", "success")
            return redirect(url_for("admin"))
        return render_template("admin.html", inventory=inventory)