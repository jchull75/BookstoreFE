# BookstoreFE

A Flask-based online bookstore with SQLite backend.

## Features
- **Customers**: Signup, login, browse/search books, order books, manage cart, cancel orders, set shipping address.
- **Admin**: Add books, view inventory (login as `admin`).

## Setup
1. Clone the repo: `git clone https://github.com/jchull75/BookstoreFE.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variable:
   - Linux/Mac: `export SECRET_KEY=your_secret_key`
   - Windows: `set SECRET_KEY=your_secret_key`
   - Or use `.env`: `SECRET_KEY=your_secret_key`
4. Run: `python app.py`
5. Visit: `http://localhost:5000`

## Testing
Run `pytest test_app.py` after setting up the app.

## Notes
- Default admin: Username `admin`, password set during signup (e.g., `adminpass`).
- Passwords are hashed with SHA-256 via `werkzeug.security`.
- Deployable to Render/Heroku with `Procfile`: `web: python app.py`.

## Deployment
Add a `Procfile` with `web: python app.py` and set `PORT` env var (default 5000).