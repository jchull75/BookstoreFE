from flask import render_template, request, redirect, url_for, flash
from database_helper import DatabaseHelper

db_helper = DatabaseHelper()

def register_routes(app):
    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            if db_helper.login_user(username, password):
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
        books = []
        if request.method == "POST" and "browse" in request.form:
            books = db_helper.get_all_books()
        return render_template("bookstore.html", books=books)