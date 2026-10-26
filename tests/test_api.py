from datetime import datetime, timedelta, timezone


def test_register_login_and_profile(client):
    registration = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "correct-horse-battery"},
    )
    assert registration.status_code == 201
    assert "password" not in registration.json()
    login = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "correct-horse-battery"},
    )
    assert login.status_code == 200
    profile = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"


def test_duplicate_email_and_invalid_login(client):
    payload = {"email": "alice@example.com", "password": "correct-horse-battery"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409
    assert client.post("/auth/login", json={**payload, "password": "wrong-password"}).status_code == 401


def test_task_crud_and_validation(client, auth_headers):
    created = client.post("/tasks", headers=auth_headers, json={"title": "Write tests", "priority": 1})
    assert created.status_code == 201
    task_id = created.json()["id"]
    updated = client.patch(
        f"/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "in_progress", "description": "Cover the API"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert client.patch(f"/tasks/{task_id}", headers=auth_headers, json={"title": None}).status_code == 422
    assert client.patch(f"/tasks/{task_id}", headers=auth_headers, json={"status": None}).status_code == 422
    assert client.post("/tasks", headers=auth_headers, json={"title": "", "priority": 9}).status_code == 422
    assert client.delete(f"/tasks/{task_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{task_id}", headers=auth_headers).status_code == 404


def test_task_ownership_is_enforced(client, auth_headers):
    task = client.post("/tasks", headers=auth_headers, json={"title": "Private"}).json()
    client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "correct-horse-battery"},
    )
    token = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "correct-horse-battery"},
    ).json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/tasks/{task['id']}", headers=bob_headers).status_code == 404
    assert client.patch(f"/tasks/{task['id']}", headers=bob_headers, json={"title": "stolen"}).status_code == 404
    assert client.delete(f"/tasks/{task['id']}", headers=bob_headers).status_code == 404


def test_list_filters_pagination_and_sorting(client, auth_headers):
    client.post("/tasks", headers=auth_headers, json={"title": "Later", "status": "todo", "priority": 2,
                                                      "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()})
    client.post("/tasks", headers=auth_headers, json={"title": "Sooner", "status": "todo", "priority": 2,
                                                      "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
    client.post("/tasks", headers=auth_headers, json={"title": "Other", "status": "done", "priority": 4})
    response = client.get("/tasks?status=todo&priority=2&page=1&limit=1&sort=asc", headers=auth_headers)
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 2
    assert result["items"][0]["title"] == "Sooner"
    assert len(result["items"]) == 1


def test_stats_count_statuses_and_overdue_tasks(client, auth_headers):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    client.post("/tasks", headers=auth_headers, json={"title": "Overdue", "due_date": yesterday})
    client.post("/tasks", headers=auth_headers, json={"title": "Complete overdue", "status": "done", "due_date": yesterday})
    client.post("/tasks", headers=auth_headers, json={"title": "In progress", "status": "in_progress"})
    stats = client.get("/tasks/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert stats.json() == {"by_status": {"todo": 1, "in_progress": 1, "done": 1}, "overdue": 1}


def test_authentication_is_required(client):
    assert client.get("/tasks").status_code == 401
