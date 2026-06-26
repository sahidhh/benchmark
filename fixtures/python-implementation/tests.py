"""Expected behavior — all tests must pass after implementation."""
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_create_task(client):
    r = client.post("/tasks", json={"title": "Write tests"})
    assert r.status_code == 201
    assert r.json["title"] == "Write tests"
    assert r.json["done"] is False
    assert "id" in r.json


def test_create_task_missing_title_returns_400(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400


def test_create_task_empty_title_returns_400(client):
    r = client.post("/tasks", json={"title": ""})
    assert r.status_code == 400


def test_get_task(client):
    r = client.post("/tasks", json={"title": "Buy milk"})
    task_id = r.json["id"]
    r2 = client.get(f"/tasks/{task_id}")
    assert r2.status_code == 200
    assert r2.json["title"] == "Buy milk"


def test_get_task_not_found(client):
    r = client.get("/tasks/9999")
    assert r.status_code == 404


def test_update_task_mark_done(client):
    r = client.post("/tasks", json={"title": "Fix bug"})
    task_id = r.json["id"]
    r2 = client.patch(f"/tasks/{task_id}", json={"done": True})
    assert r2.status_code == 200
    assert r2.json["done"] is True


def test_update_task_not_found(client):
    r = client.patch("/tasks/9999", json={"done": True})
    assert r.status_code == 404


def test_delete_task(client):
    r = client.post("/tasks", json={"title": "Clean up"})
    task_id = r.json["id"]
    r2 = client.delete(f"/tasks/{task_id}")
    assert r2.status_code == 204
    r3 = client.get(f"/tasks/{task_id}")
    assert r3.status_code == 404


def test_delete_task_not_found(client):
    r = client.delete("/tasks/9999")
    assert r.status_code == 404


def test_list_tasks(client):
    client.post("/tasks", json={"title": "A"})
    client.post("/tasks", json={"title": "B"})
    r = client.get("/tasks")
    assert r.status_code == 200
    assert len(r.json) >= 2
