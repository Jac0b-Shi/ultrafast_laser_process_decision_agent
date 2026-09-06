import pytest
from fastapi import HTTPException, Request

from app.settings import get_settings
from app.services import rate_limit


def request(direct, forwarded):
    return Request({"type":"http","method":"GET","path":"/","headers":[(b"x-forwarded-for",forwarded.encode())],"client":(direct,1234),"server":("test",80),"scheme":"http","query_string":b""})


def test_forwarded_ip_only_from_configured_proxy(monkeypatch):
    monkeypatch.setenv("LASER_TRUSTED_PROXIES", "100.64.0.1")
    get_settings.cache_clear()
    assert rate_limit.client_key(request("100.64.0.1","203.0.113.8")) == "203.0.113.8"
    assert rate_limit.client_key(request("100.64.0.1","1.2.3.4, 203.0.113.8")) == "203.0.113.8"
    assert rate_limit.client_key(request("100.64.0.1","203.0.113.8, 100.64.0.1")) == "203.0.113.8"
    assert rate_limit.client_key(request("198.51.100.2","203.0.113.8")) == "198.51.100.2"
    get_settings.cache_clear()


def test_database_rate_and_global_lease(tmp_path, monkeypatch):
    monkeypatch.setenv("LASER_EXPERIMENTS_DIR", str(tmp_path))
    get_settings.cache_clear()
    rate_limit.consume("test", "client", ((60,2),))
    rate_limit.consume("test", "client", ((60,2),))
    with pytest.raises(HTTPException) as error:
        rate_limit.consume("test", "client", ((60,2),))
    assert error.value.status_code == 429
    first=rate_limit.acquire("work",2);second=rate_limit.acquire("work",2)
    assert first and second and rate_limit.acquire("work",2) is None
    rate_limit.release("work",first)
    assert rate_limit.acquire("work",2)
    get_settings.cache_clear()
