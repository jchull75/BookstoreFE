from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database_helper import DatabaseHelper
import os
import sqlite3
import logging
from datetime import datetime
import random

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
db_helper = DatabaseHelper()

sort_options = {
    'default': 'Default',
    'title_asc': 'Title (A-Z)',
    'title_desc': 'Title (Z-A)',
    'price_asc': 'Price (Low to High)',
    'price_desc': 'Price (High to Low)'
}

def get_context():
    is_admin = False
    if 'user' in session:
        is_admin = session.get('user') == 'admin'
    return {'is_admin': is_admin}

@app.route('/')
def home():
    return render_template('index.html', **get_context())

@app.route('/bookstore')
def bookstore():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    sort = request.args.get('sort', 'default')
    books, total_books = db_helper.get_all_books(page, per_page)
    total_pages = (total_books + per_page - 1) // per_page
    return render_template('bookstore.html', books=books, page=page, total_pages=total_pages, sort=sort, sort_options=sort_options, **get_context())

@app.route('/get_book_details/<int:book_id>')
def get_book_details(book_id):
    book = db_helper.get_book_by_id(book_id)
    if book:
        reviews = db_helper.get_reviews_for_book(book_id)
        review_text = '<ul class="list-unstyled">' + ''.join(f'<li><strong>{r["first_name"]} {r["last_name"]}</strong> ({r["rating"]}/5): {r["comment"]} - {r["review_date"]}</li>' for r in reviews) + '</ul>' if reviews else 'No reviews yet.'
        return {
            'title': book['title'],
            'author': book['author'],
            'price': book['price'],
            'description': book['description'] or 'A captivating tale of adventure and mystery, spanning continents and centuries, with richly drawn characters.',
            'reviews': review_text,
            'cover_image': book['cover_image'],
            'book_id': book_id  # Added for Add to Cart
        }
    return {'error': 'Book not found'}, 404

@app.route('/get_bestseller')
def get_bestseller():
    conn = sqlite3.connect(db_helper.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, COUNT(o.order_id) as order_count
        FROM Books b
        LEFT JOIN Orders o ON b.book_id = o.book_id
        GROUP BY b.book_id
        ORDER BY order_count DESC
        LIMIT 1
    ''')
    bestseller = cursor.fetchone()
    conn.close()
    if bestseller:
        reviews = db_helper.get_reviews_for_book(bestseller['book_id'])
        review_text = '<ul class="list-unstyled">' + ''.join(f'<li><strong>{r["first_name"]} {r["last_name"]}</strong> ({r["rating"]}/5): {r["comment"]} - {r["review_date"]}</li>' for r in reviews) + '</ul>' if reviews else 'No reviews yet.'
        return {
            'title': bestseller['title'],
            'author': bestseller['author'],
            'price': bestseller['price'],
            'description': bestseller['description'] or 'A captivating tale of adventure and mystery, spanning continents and centuries, with richly drawn characters.',
            'reviews': review_text,
            'cover_image': bestseller['cover_image'],
            'book_id': bestseller['book_id']  # Added for Add to Cart
        }
    return {'error': 'No bestseller available'}, 404

@app.route('/get_order_details/<int:order_id>')
def get_order_details(order_id):
    conn = sqlite3.connect(db_helper.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.*, b.title, b.price
        FROM Orders o 
        JOIN Books b ON o.book_id = b.book_id 
        WHERE o.order_id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    conn.close()
    if order:
        return {
            'order_id': order['order_id'],
            'book_title': order['title'],
            'quantity': order['quantity'],
            'price': order['price'],
            'payment_method': order['payment_method'],
            'payment_details': order['payment_details'] if order['payment_details'] else 'N/A',
            'shipping_address': f"{order['shipping_street']}, {order['shipping_city']}, {order['shipping_state']} {order['shipping_zipcode']}",
            'status': order['status'],
            'order_date': order['order_date']
        }
    return {'error': 'Order not found'}, 404

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user' not in session or session.get('user') == 'admin':
        return jsonify({'error': 'Please log in as a customer to submit a review'}), 401
    
    data = request.json
    book_id = data.get('book_id')
    rating = data.get('rating')
    comment = data.get('comment')
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']

    if not all([book_id, rating, comment]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = sqlite3.connect(db_helper.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Reviews (book_id, customer_email, rating, comment, review_date)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (book_id, customer_email, rating, comment))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Review submitted successfully'}), 200

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session or session.get('user') == 'admin':
        flash('Please log in as a customer to add to cart.', 'danger')
        return redirect(url_for('customer_login'))
    
    book_id = request.form['book_id']
    quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    book_id_str = str(book_id)
    if book_id_str in cart:
        cart[book_id_str]['quantity'] += quantity
    else:
        book = db_helper.get_book_by_id(book_id)
        if book:
            cart[book_id_str] = {'title': book['title'], 'quantity': quantity, 'price': book['price']}
    session['cart'] = cart
    flash('Book added to cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'user' not in session or session.get('user') == 'admin':
        flash('Please log in as a customer to add to wishlist.', 'danger')
        return redirect(url_for('customer_login'))
    
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']
    book_id = request.form['book_id']
    quantity = int(request.form.get('quantity', 1))
    
    db_helper.add_to_wishlist(customer_email, book_id, quantity)
    flash('Book added to wishlist!', 'success')
    return redirect(url_for('profile'))

@app.route('/buy_now', methods=['POST'])
def buy_now():
    if 'user' not in session or session.get('user') == 'admin':
        flash('Please log in as a customer to buy now.', 'danger')
        return redirect(url_for('customer_login'))
    
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']
    book_id = request.form['book_id']
    quantity = int(request.form.get('quantity', 1))
    profile = db_helper.get_user_profile_by_identifier(session['user'])
    
    order_id = db_helper.add_order(
        customer_email,
        book_id,
        profile['street'],
        profile['city'],
        profile['state'],
        profile['zipcode'],
        'Credit Card',  # Default payment method; can be extended to support others
        quantity
    )
    if order_id:
        flash('Purchase successful!', 'success')
    else:
        flash('Not enough stock to complete purchase.', 'danger')
    return redirect(url_for('profile'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user' not in session or session.get('user') == 'admin':
        return redirect(url_for('customer_login'))
    
    book_id = request.form['book_id']
    cart = session.get('cart', {})
    book_id_str = str(book_id)
    if book_id_str in cart:
        del cart[book_id_str]
        session['cart'] = cart
        flash('Book removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user' not in session or session.get('user') == 'admin':
        flash('Please log in as a customer to checkout.', 'danger')
        return redirect(url_for('customer_login'))
    
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']
    profile = db_helper.get_user_profile_by_identifier(session['user'])
    cart = session.get('cart', {})
    
    if not cart:
        flash('Your cart is empty.', 'danger')
        return redirect(url_for('cart'))
    
    payment_method = request.form.get('payment_method', 'Credit Card')
    payment_details = {}
    
    if payment_method == 'Credit Card':
        payment_details = {
            'card_number': request.form.get('card_number', '4111 1111 1111 1111'),
            'expiry': request.form.get('expiry', '12/25'),
            'cvv': request.form.get('cvv', '123')
        }
    elif payment_method == 'PayPal':
        payment_details = {
            'paypal_email': request.form.get('paypal_email', 'user@example.com')
        }
    
    full_payment_info = f"{payment_method}: {payment_details}"
    logger.debug(f"Checkout payment info: {full_payment_info}")
    
    for book_id, item in cart.items():
        order_id = db_helper.add_order(
            customer_email,
            int(book_id),
            profile['street'],
            profile['city'],
            profile['state'],
            profile['zipcode'],
            payment_method,
            item['quantity'],
            payment_details
        )
        if not order_id:
            flash(f"Not enough stock for {item['title']}.", 'danger')
            return redirect(url_for('cart'))
    
    session.pop('cart', None)
    flash('Order placed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/cart')
def cart():
    if 'user' not in session or session.get('user') == 'admin':
        flash('Please log in as a customer to view your cart.', 'danger')
        return redirect(url_for('customer_login'))
    cart = session.get('cart', {})
    return render_template('cart.html', cart=cart, **get_context())

@app.route('/order_from_wishlist', methods=['POST'])
def order_from_wishlist():
    if 'user' not in session or session.get('user') == 'admin':
        return redirect(url_for('customer_login'))
    
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']
    book_id = request.form['book_id']
    quantity = int(request.form['quantity'])
    profile = db_helper.get_user_profile_by_identifier(session['user'])
    book = db_helper.get_book_by_id(book_id)
    
    order_id = db_helper.add_order(
        customer_email,
        book_id,
        profile['street'],
        profile['city'],
        profile['state'],
        profile['zipcode'],
        'Credit Card',
        quantity
    )
    if order_id:
        db_helper.remove_from_wishlist(customer_email, book_id)
        flash('Order placed from wishlist!', 'success')
    else:
        flash('Not enough stock to place order.', 'danger')
    return redirect(url_for('profile'))

@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    if 'user' not in session or session.get('user') == 'admin':
        return redirect(url_for('customer_login'))
    
    order_id = request.form['order_id']
    if db_helper.cancel_order(order_id):
        flash('Order cancelled successfully!', 'success')
    else:
        flash('Order could not be cancelled (already processed or not found).', 'danger')
    return redirect(url_for('profile'))

@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'user' not in session or session.get('user') == 'admin':
        return redirect(url_for('customer_login'))
    
    customer_email = db_helper.get_user_profile_by_identifier(session['user'])['email']
    book_id = request.form['book_id']
    db_helper.remove_from_wishlist(customer_email, book_id)
    flash('Book removed from wishlist!', 'success')
    return redirect(url_for('profile'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session or session.get('user') == 'admin':
        return redirect(url_for('customer_login'))
    user_identifier = session['user']
    profile_data = db_helper.get_user_profile_by_identifier(user_identifier)
    if not profile_data:
        logger.error(f"No profile found for user: {user_identifier}")
        flash('Profile not found. Please log in again.')
        session.pop('user', None)
        return redirect(url_for('customer_login'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email_new = request.form['email']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        mailing_street = request.form['mailing_street']
        mailing_city = request.form['mailing_city']
        mailing_state = request.form['mailing_state']
        mailing_zipcode = request.form['mailing_zipcode']

        db_helper.update_user_profile(profile_data['email'], first_name, last_name, email_new, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode)
        if email_new != profile_data['email']:
            session['user'] = email_new
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    wishlist = db_helper.get_user_wishlist(profile_data['email'])
    orders = db_helper.get_user_orders(profile_data['email'])
    return render_template('profile.html', profile=profile_data, wishlist=wishlist, orders=orders, **get_context())

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        
        if db_helper.register_user(first_name, email, password, last_name, street, city, state, zipcode):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('customer_login'))
        else:
            flash('Email already exists.', 'danger')
    return render_template('signup.html', **get_context())

@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        logger.debug(f"Customer login attempt: identifier={identifier}, password={password}")
        user = db_helper.login_user(identifier, password)
        if user:
            session['user'] = identifier
            logger.debug(f"Customer login successful, session set for {identifier}")
            return redirect(url_for('profile'))
        flash('Invalid credentials.', 'danger')
        logger.debug("Customer login failed: invalid credentials")
    return render_template('customer_login.html', **get_context())

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logger.debug(f"Admin login attempt: username={username}, password={password}")
        if username == 'admin' and password == 'admintest':
            session['user'] = 'admin'
            logger.debug("Admin login successful, session set")
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.', 'danger')
        logger.debug("Admin login failed: invalid credentials")
    return render_template('admin_login.html', **get_context())

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user' not in session or session.get('user') != 'admin':
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if 'supplier_group_id' in request.form:
            group_id = request.form['supplier_group_id']
            status = request.form['status']
            db_helper.update_supplier_order_status(group_id, status)
            flash(f"Supplier Order Group {group_id} status updated to {status}", 'success')
        elif 'customer_order_id' in request.form:
            order_id = request.form['customer_order_id']
            status = request.form['status']
            db_helper.update_order_status(order_id, status)
            flash(f"Customer Order {order_id} status updated to {status}", 'success')
        return redirect(url_for('admin_dashboard'))

    supplier_orders = db_helper.get_all_supplier_orders()
    customer_orders = db_helper.get_all_orders()
    books = db_helper.get_all_books(page=1, per_page=100)[0]
    grouped_orders = {}
    for order in supplier_orders:
        group_id = order['group_order_id']
        if group_id not in grouped_orders:
            grouped_orders[group_id] = {'supplier': order['supplier'], 'books': [], 'total_price': 0.0, 'order_date': order['order_date'], 'status': order['status']}
        grouped_orders[group_id]['books'].append(order)
        grouped_orders[group_id]['total_price'] += order['quantity'] * order['price']

    return render_template('admin_dashboard.html', grouped_orders=grouped_orders, customer_orders=customer_orders, books=books, **get_context())

@app.route('/supplier_orders', methods=['GET', 'POST'])
def supplier_orders():
    if 'user' not in session or session.get('user') != 'admin':
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        supplier = request.form['supplier']
        book_ids = request.form.getlist('book_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        group_order_id = int(datetime.now().timestamp() * 1000)
        total_price = 0.0

        conn = sqlite3.connect(db_helper.db_path)
        cursor = conn.cursor()

        for book_id, qty, price in zip(book_ids, quantities, prices):
            if book_id and qty and price:
                qty = int(qty)
                price = float(price)
                cursor.execute("SELECT book_id FROM Books WHERE book_id = ?", (book_id,))
                book = cursor.fetchone()
                if book:
                    total_price += qty * price
                    db_helper.add_supplier_order(supplier, book_id, qty, price, group_order_id)
                else:
                    flash(f"Book ID '{book_id}' not found", 'danger')
                    conn.close()
                    return redirect(url_for('supplier_orders'))

        conn.close()
        flash(f"Supplier order added with total price ${total_price:.2f}", 'success')
        return redirect(url_for('supplier_orders'))

    supplier_orders = db_helper.get_all_supplier_orders()
    books = db_helper.get_all_books(page=1, per_page=100)[0]
    grouped_orders = {}
    for order in supplier_orders:
        group_id = order['group_order_id']
        if group_id not in grouped_orders:
            grouped_orders[group_id] = {'supplier': order['supplier'], 'books': [], 'total_price': 0.0, 'order_date': order['order_date'], 'status': order['status']}
        grouped_orders[group_id]['books'].append(order)
        grouped_orders[group_id]['total_price'] += order['quantity'] * order['price']

    return render_template('admin_supplier_orders.html', grouped_orders=grouped_orders, books=books, **get_context())

@app.route('/admin/inventory', methods=['GET', 'POST'])
def admin_inventory():
    if 'user' not in session or session.get('user') != 'admin':
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        if 'add_book' in request.form:
            title = request.form['title']
            author = request.form['author']
            genre = request.form['genre']
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            isbn = request.form['isbn']
            description = request.form['description']
            db_helper.add_book(title, author, genre, price, quantity, isbn, description)
            flash(f"Book '{title}' added successfully!", 'success')
        elif 'book_id' in request.form:
            book_id = request.form['book_id']
            quantity = int(request.form['quantity'])
            db_helper.update_book_quantity(book_id, quantity)
            flash(f"Quantity updated for book ID {book_id}", 'success')
        return redirect(url_for('admin_inventory'))
    books = db_helper.get_all_books(page=1, per_page=100)[0]
    return render_template('admin_inventory.html', books=books, **get_context())

@app.route('/admin/orders', methods=['GET', 'POST'])
def admin_orders():
    if 'user' not in session or session.get('user') != 'admin':
        return redirect(url_for('admin_login'))
    customer_orders = db_helper.get_all_orders()
    return render_template('admin_orders.html', customer_orders=customer_orders, **get_context())

@app.route('/admin/remove_book', methods=['POST'])
def remove_book():
    if 'user' not in session or session.get('user') != 'admin':
        return redirect(url_for('admin_login'))
    book_id = request.form['book_id']
    db_helper.remove_book(book_id)
    flash(f"Book with ID {book_id} removed successfully!")
    return redirect(url_for('admin_inventory'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)