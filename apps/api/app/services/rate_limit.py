"""SQLite-backed rate counters and cross-worker work leases."""
from __future__ import annotations

import hashlib
import ipaddress
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException, Request

from app.services import agent_store as store
from app.settings import get_settings


def client_key(request: Request) -> str:
    direct = request.client.host if request.client else "unknown"
    trusted = set(get_settings().trusted_proxies)
    if direct in trusted:
        candidates = [item.strip() for item in request.headers.get("x-forwarded-for", "").split(",")]
        for candidate in reversed(candidates):
            try:
                normalized = str(ipaddress.ip_address(candidate))
            except ValueError:
                continue
            if normalized not in trusted:
                return normalized
    return direct


def consume(scope: str, key: str, limits: tuple[tuple[int, int], ...]):
    """Consume one event when every ``(window_seconds, maximum)`` limit allows it."""
    instant = store.now()
    digest = hashlib.sha256(key.encode()).hexdigest()
    longest = max(window for window, _ in limits)
    with store.database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM rate_events WHERE scope=? AND created<=?", (scope, (instant-timedelta(seconds=longest)).isoformat()))
        for window, maximum in limits:
            count = conn.execute("SELECT count(*) FROM rate_events WHERE scope=? AND key_hash=? AND created>?", (scope,digest,(instant-timedelta(seconds=window)).isoformat())).fetchone()[0]
            if count >= maximum:
                raise HTTPException(429, "请求过于频繁，请稍后重试", headers={"Retry-After": str(window)})
        conn.execute("INSERT INTO rate_events(scope,key_hash,created) VALUES(?,?,?)", (scope,digest,instant.isoformat()))


def acquire(name: str, slots: int, ttl_seconds: int = 300) -> str | None:
    instant = store.now()
    owner = str(uuid4())
    with store.database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for slot in range(slots):
            row = conn.execute("SELECT expires FROM work_leases WHERE name=? AND slot=?", (name,slot)).fetchone()
            if row is None:
                conn.execute("INSERT INTO work_leases VALUES(?,?,?,?)", (name,slot,owner,(instant+timedelta(seconds=ttl_seconds)).isoformat()))
                return owner
            if row["expires"] <= instant.isoformat():
                conn.execute("UPDATE work_leases SET owner=?,expires=? WHERE name=? AND slot=?", (owner,(instant+timedelta(seconds=ttl_seconds)).isoformat(),name,slot))
                return owner
    return None


def release(name: str, owner: str):
    with store.database() as conn:
        conn.execute("DELETE FROM work_leases WHERE name=? AND owner=?", (name,owner))
