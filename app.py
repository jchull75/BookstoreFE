from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Debug route
@app.route("/test")
def test():
    return "Test route works!"

# Import routes after app is defined
from routes import register_routes  # We'll add this function
register_routes(app)  # Explicitly register routes

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)