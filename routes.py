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
        books = db_helper.get_all_books()
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
        address_data = db_helper.get_user_address(session['username'])
        if request.method == "POST" and "checkout" in request.form:
            shipping_street = request.form["shipping_street"]
            shipping_city = request.form["shipping_city"]
            shipping_state = request.form["shipping_state"]
            shipping_zipcode = request.form["shipping_zipcode"]
            payment_method = "Credit Card: 1234 (Test Mode)"
            for book_id in cart:
                order_id = db_helper.add_order(session['username'], book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method)
                if order_id is None:
                    flash(f"❌ Cannot order book ID {book_id}: Out of stock!", "error")
                    return redirect(url_for("cart"))
            session['cart'] = []
            flash("✅ Order placed successfully!", "success")
            return redirect(url_for("bookstore"))
        return render_template("cart.html", books=books, address=address_data)

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if 'username' not in session:
            flash("❌ Please log in to access your profile.", "error")
            return redirect(url_for("login"))
        address_data = db_helper.get_user_address(session['username'])
        if request.method == "POST":
            street = request.form["street"]
            city = request.form["city"]
            state = request.form["state"]
            zipcode = request.form["zipcode"]
            db_helper.update_address(session['username'], street, city, state, zipcode)
            flash("✅ Address updated!", "success")
            address_data = {"street": street, "city": city, "state": state, "zipcode": zipcode}
        return render_template("profile.html", address=address_data)

    @app.route("/wishlist", methods=["GET", "POST"])
    def wishlist():
        if 'username' not in session:
            flash("❌ Please log in to access your wishlist.", "error")
            return redirect(url_for("login"))
        wishlist_ids = db_helper.get_user_wishlist(session['username'])
        wishlist_books = [book for book in db_helper.get_all_books() if book["book_id"] in wishlist_ids]
        address_data = db_helper.get_user_address(session['username'])
        if request.method == "POST" and "order_from_wishlist" in request.form:
            book_ids = request.form.getlist("book_ids")  # Get selected books
            if not book_ids:
                flash("❌ No books selected to order!", "error")
            else:
                payment_method = "Credit Card: 1234 (Test Mode)"
                for book_id in map(int, book_ids):
                    order_id = db_helper.add_order(session['username'], book_id, 
                                                  address_data["street"], address_data["city"], 
                                                  address_data["state"], address_data["zipcode"], payment_method)
                    if order_id:
                        db_helper.remove_from_wishlist(session['username'], book_id)
                    else:
                        flash(f"❌ Cannot order book ID {book_id}: Out of stock!", "error")
                        return redirect(url_for("wishlist"))
                flash("✅ Selected books ordered successfully!", "success")
            return redirect(url_for("wishlist"))
        return render_template("wishlist.html", wishlist_books=wishlist_books, address=address_data)

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
            quantity = int(request.form["quantity"])
            db_helper.add_book(title, author, genre, price, quantity)
            flash("✅ Book added!", "success")
            return redirect(url_for("bookstore"))
        return render_template("admin_add_book.html")

    @app.route("/admin/inventory", methods=["GET", "POST"])
    def admin_inventory():
        if 'username' not in session or session['username'] != 'admin':
            flash("❌ Admin access only!", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            if "update_quantity" in request.form:
                book_id = int(request.form["book_id"])
                quantity = int(request.form["quantity"])
                if quantity < 0:
                    flash("❌ Quantity cannot be negative!", "error")
                else:
                    db_helper.update_book_quantity(book_id, quantity)
                    flash("✅ Quantity updated successfully!", "success")
            elif "order_from_supplier" in request.form:
                book_id = int(request.form["book_id"])
                supplier_name = request.form["supplier_name"]
                amount = int(request.form["amount"])
                expected_delivery_date = request.form.get("expected_delivery_date") or None
                db_helper.add_supplier_inventory_order(book_id, supplier_name, amount, expected_delivery_date)
                flash("✅ Supplier order placed!", "success")
            return redirect(url_for("admin_inventory"))
        books = db_helper.get_all_books()
        analytics = db_helper.get_sales_analytics()
        return render_template("admin_inventory.html", books=books, analytics=analytics)

    @app.route("/admin/order_books", methods=["GET", "POST"])
    def admin_order_books():
        if 'username' not in session or session['username'] != 'admin':
            flash("❌ Admin access only!", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            supplier_inventory_order_id = int(request.form["supplier_inventory_order_id"])
            db_helper.complete_supplier_inventory_order(supplier_inventory_order_id)
            flash("✅ Supplier inventory order completed!", "success")
            return redirect(url_for("admin_order_books"))
        supplier_inventory_orders = db_helper.get_supplier_inventory_orders("Pending")
        return render_template("admin_order_books.html", supplier_inventory_orders=supplier_inventory_orders)

    @app.route("/admin/orders", methods=["GET"])
    def admin_orders():
        if 'username' not in session or session['username'] != 'admin':
            flash("❌ Admin access only!", "error")
            return redirect(url_for("login"))
        all_orders = db_helper.get_all_orders()
        return render_template("admin_orders.html", orders=all_orders)

    @app.route("/add_to_cart", methods=["POST"])
    def add_to_cart():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = int(request.form.get("book_id"))
        cart = session.get('cart', [])
        book = next((b for b in db_helper.get_all_books() if b["book_id"] == book_id), None)
        if book and book["quantity"] > 0 and book_id not in cart:
            cart.append(book_id)
            session['cart'] = cart
            return jsonify({'message': 'Book added to cart'}), 200
        elif not book:
            return jsonify({'error': 'Book not found'}), 404
        elif book["quantity"] <= 0:
            return jsonify({'error': 'Book out of stock'}), 400
        return jsonify({'message': 'Book already in cart'}), 200

    @app.route("/add_to_wishlist", methods=["POST"])
    def add_to_wishlist():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = int(request.form.get("book_id"))
        db_helper.add_to_wishlist(session['username'], book_id)
        return jsonify({'message': 'Book added to wishlist'}), 200

    @app.route("/remove_from_wishlist", methods=["POST"])
    def remove_from_wishlist():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = int(request.form.get("book_id"))
        db_helper.remove_from_wishlist(session['username'], book_id)
        return jsonify({'message': 'Book removed from wishlist'}), 200

    @app.route("/orders", methods=["POST"])
    def create_order():
        if 'username' not in session:
            return jsonify({'error': 'Must be logged in'}), 401
        book_id = request.form.get("book_id")
        if not book_id:
            return jsonify({'error': 'Book ID required'}), 400
        address_data = db_helper.get_user_address(session['username'])
        payment_method = "Credit Card: 1234 (Test Mode)"
        order_id = db_helper.add_order(session['username'], int(book_id), 
                                      address_data["street"], address_data["city"], 
                                      address_data["state"], address_data["zipcode"], payment_method)
        if order_id is None:
            return jsonify({'error': 'Book out of stock'}), 400
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