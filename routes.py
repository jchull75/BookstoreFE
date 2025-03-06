from flask import session, redirect, url_for

def admin_required(f):
    """Decorator to protect admin-only routes"""
    def wrap(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash("Access denied! Admins only.", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrap
