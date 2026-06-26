from flask import Flask, request, jsonify
from database import get_user, create_session
from auth import verify_token, require_auth

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = get_user(data["username"], data["password"])
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_session(user["id"])
    return jsonify({"token": token})


@app.route("/api/profile", methods=["GET"])
@require_auth
def profile():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user_id = verify_token(token)
    user = get_user(user_id=user_id)
    return jsonify(user)


@app.route("/api/admin/users", methods=["GET"])
@require_auth
def list_users():
    # TODO: restrict to admin only
    from database import list_all_users
    return jsonify(list_all_users())


if __name__ == "__main__":
    app.run(debug=True)
