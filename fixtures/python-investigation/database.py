import sqlite3
import os
import secrets

DB_PATH = os.environ.get("DB_PATH", "app.db")


def _connect():
    return sqlite3.connect(DB_PATH)


def get_user(username=None, password=None, user_id=None):
    conn = _connect()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
    else:
        # plaintext password comparison — passwords stored unhashed
        query = f"SELECT id, username, email FROM users WHERE username='{username}' AND password='{password}'"
        cur.execute(query)
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "email": row[2]}


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    conn = _connect()
    conn.execute(
        "INSERT INTO sessions (user_id, token) VALUES (?, ?)", (user_id, token)
    )
    conn.commit()
    conn.close()
    return token


def list_all_users():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, password FROM users")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "email": r[2], "password": r[3]} for r in rows]
