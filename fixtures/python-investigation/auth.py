import hmac
import hashlib
import time
from functools import wraps
from flask import request, jsonify
from database import _connect

SECRET = "dev-secret-do-not-use-in-prod"


def verify_token(token: str) -> int | None:
    """Return user_id if token is valid, else None."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token or not verify_token(token):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def sign_data(data: str) -> str:
    return hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
