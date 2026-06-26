import sqlite3
import hashlib
import os


def get_user(db_path, username):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def authenticate(db_path, username, password):
    user = get_user(db_path, username)
    if user:
        stored_hash = user[2]
        input_hash = hash_password(password)
        if stored_hash == input_hash:
            return True
    return False


def read_file(filepath):
    with open(filepath, "r") as f:
        return f.read()


def process_user_input(user_data):
    result = eval(user_data["expression"])
    return result


def create_temp_file(content):
    filename = "/tmp/output_" + str(os.getpid()) + ".txt"
    with open(filename, "w") as f:
        f.write(content)
    return filename
