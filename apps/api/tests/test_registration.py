import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings
from app.services import agent_store as store


def test_admin_email_configuration_and_verified_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("LASER_EXPERIMENTS_DIR", str(tmp_path))
    monkeypatch.setenv("LASER_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LASER_ADMIN_PASSWORD", "admin-password-123")
    get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.post("/api/agent/login", json={"username":"admin","password":"admin-password-123"}).status_code == 200
    config = {
        "enabled": True, "host": "smtp.feishu.cn", "port": 465, "security": "ssl",
        "username": "mailer@example.test", "sender_email": "mailer@example.test",
        "sender_name": "Laser", "public_base_url": "https://laser.example.com",
        "verification_ttl_minutes": 30, "password": "dedicated-secret",
    }
    saved = client.put("/api/agent/admin/email", json=config)
    assert saved.status_code == 200 and saved.json()["has_password"] is True
    assert "password" not in client.get("/api/agent/admin/email").json()

    from app.services import email_registration
    deliveries = []
    monkeypatch.setattr(email_registration, "_send", lambda recipient, subject, text: deliveries.append((recipient, subject, text)))
    client.post("/api/agent/logout")
    response = client.post("/api/agent/register", json={"username":"new-user","email":"NEW@EXAMPLE.COM","password":"new-user-password"})
    assert response.status_code == 200 and len(deliveries) == 1
    token = re.search(r"token=([^\s]+)", deliveries[0][2]).group(1)
    verified = client.post("/api/agent/register/verify", json={"token":token})
    assert verified.status_code == 200 and verified.json()["username"] == "new-user"
    assert client.post("/api/agent/register/verify", json={"token":token}).status_code == 409
    assert client.post("/api/agent/login", json={"username":"new-user","password":"new-user-password"}).status_code == 200
    with store.database() as conn:
        row = conn.execute("SELECT admin,email,credit_limit FROM users WHERE username='new-user'").fetchone()
    assert dict(row) == {"admin":0,"email":"new@example.com","credit_limit":0}
    get_settings.cache_clear()


def test_registration_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("LASER_EXPERIMENTS_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = TestClient(create_app())
    response = client.post("/api/agent/register", json={"username":"new-user","email":"new@example.com","password":"new-user-password"})
    assert response.status_code == 503
    get_settings.cache_clear()


def test_empty_registration_email_is_validation_error(tmp_path, monkeypatch):
    monkeypatch.setenv("LASER_EXPERIMENTS_DIR", str(tmp_path))
    monkeypatch.setenv("LASER_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LASER_ADMIN_PASSWORD", "admin-password-123")
    get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.post("/api/agent/login", json={"username":"admin","password":"admin-password-123"}).status_code == 200
    config={"enabled":True,"host":"smtp.example.com","port":465,"security":"ssl","username":"sender@example.com","sender_email":"sender@example.com","sender_name":"Laser","public_base_url":"https://laser.example.com","verification_ttl_minutes":30,"password":"secret"}
    assert client.put("/api/agent/admin/email",json=config).status_code == 200
    client.post("/api/agent/logout")
    response=client.post("/api/agent/register",json={"username":"new-user","email":"","password":"new-user-password"})
    assert response.status_code == 422
    get_settings.cache_clear()
