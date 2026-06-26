"""Task manager API — add endpoints and fix bugs described in tests.py."""
from flask import Flask, request, jsonify

app = Flask(__name__)

# in-memory store for simplicity
_tasks: dict[int, dict] = {}
_next_id = 1


@app.route("/tasks", methods=["GET"])
def list_tasks():
    return jsonify(list(_tasks.values()))


@app.route("/tasks", methods=["POST"])
def create_task():
    global _next_id
    data = request.get_json()
    # BUG: no validation — title can be missing or empty
    task = {"id": _next_id, "title": data["title"], "done": False}
    _tasks[_next_id] = task
    _next_id += 1
    return jsonify(task), 201


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    # BUG: KeyError not handled
    return jsonify(_tasks[task_id])


@app.route("/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    # BUG: missing — not implemented
    pass


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    # BUG: missing — not implemented
    pass
