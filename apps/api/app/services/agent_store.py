"""Account-scoped append-only records. SQLite transactions are the write authority."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, Request
from app.settings import get_settings


def now():
    return datetime.now(timezone.utc)


@contextmanager
def database():
    path = get_settings().experiments_dir / "agent" / "state.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT, admin INTEGER);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, owner TEXT, expires TEXT);
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,
      kind TEXT NOT NULL, entity TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS events_owner ON events(owner,kind,entity);
    """)
    from app.services.agent_schema import migrate
    migrate(conn, path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ":" + digest


def create_user(username, password, admin=False, email=None, initial=False):
    if not username.strip() or len(username) > 80 or len(password) < 12 or len(password) > 256:
        raise HTTPException(422, "用户名不能为空，密码须为 12–256 字符")
    with database() as conn:
        try:
            user_id = str(uuid4())
            conn.execute("INSERT INTO users(id,username,password,admin,email,bootstrap) VALUES(?,?,?,?,?,?)", (user_id, username.strip(), password_hash(password), int(admin), normalize_email(email), int(initial)))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "用户名已存在")
    return {"id": user_id, "username": username.strip(), "admin": bool(admin)}


def bootstrap(sync_credentials=False):
    username = os.getenv("LASER_ADMIN_USERNAME")
    password = os.getenv("LASER_ADMIN_PASSWORD")
    with database() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE bootstrap=1").fetchone()
    if not exists and username and password:
        try:
            create_user(username, password, True, initial=True)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
    with database() as conn:
        initial = conn.execute("SELECT * FROM users WHERE bootstrap=1").fetchone()
        if sync_credentials and initial and username and password:
            changed = initial['username'] != username or not hmac.compare_digest(password_hash(password, initial['password'].split(':')[0]), initial['password'])
            if changed:
                if not 1 <= len(username) <= 80 or not 12 <= len(password) <= 256:
                    raise HTTPException(503, '初始账号配置无效')
                try:
                    conn.execute('UPDATE users SET username=?,password=? WHERE id=?', (username, password_hash(password), initial['id']))
                except sqlite3.IntegrityError:
                    raise HTTPException(503, '初始用户名与数据库账号冲突')
                conn.execute('DELETE FROM sessions WHERE owner=?', (initial['id'],))
        active = conn.execute("SELECT 1 FROM users WHERE admin=1 AND enabled=1 AND bootstrap=0").fetchone()
        disabled = bool(active) or not (username and password)
        conn.execute("UPDATE users SET enabled=? WHERE bootstrap=1", (0 if disabled else 1,))
        if disabled:
            conn.execute("DELETE FROM sessions WHERE owner IN (SELECT id FROM users WHERE bootstrap=1)")


def normalize_email(email):
    import re
    if email is None or email == "":return None
    if not isinstance(email,str):raise HTTPException(422,"邮箱格式无效")
    email = email.strip().lower()
    if len(email)>254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "邮箱格式无效")
    return email


def public_user(row):
    data={k:row[k] for k in ('id','username','admin','email','enabled','bootstrap','credit_limit')}
    data['avatar_url']='https://www.gravatar.com/avatar/'+hashlib.sha256(row['email'].encode()).hexdigest()+'?d=identicon&s=96' if row['email'] else None
    return data


def login(username, password):
    bootstrap(sync_credentials=True)
    if len(password) > 256:
        raise HTTPException(401, "用户名或密码错误")
    with database() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        stored = row["password"] if row else password_hash("unavailable")
        valid = hmac.compare_digest(password_hash(password, stored.split(":")[0]), stored)
        if not row or not valid or not row['enabled']:
            raise HTTPException(401, "用户名或密码错误")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row["id"], (now()+timedelta(hours=12)).isoformat()))
        return token, public_user(row)


def current_user(request: Request):
    bootstrap()
    token = request.cookies.get("laser_session", "")
    with database() as conn:
        row = conn.execute("SELECT u.* FROM users u JOIN sessions s ON s.owner=u.id WHERE s.token=? AND s.expires>? AND u.enabled=1", (hashlib.sha256(token.encode()).hexdigest(), now().isoformat())).fetchone()
    if not row:
        raise HTTPException(401, "请先登录")
    return public_user(row)


def administrator(request: Request):
    user = current_user(request)
    if not user["admin"]:
        raise HTTPException(403, "仅管理员可操作")
    return user


def _project(rows):
    result = {}
    for row in rows:
        if row["action"] in ("create", "revise"):
            payload = json.loads(row["payload"])
            result[row["entity"]] = {**payload, "id": row["entity"], "deleted_at": None}
        elif row["entity"] in result:
            result[row["entity"]]["deleted_at"] = row["created"] if row["action"] == "delete" else None
        if row["entity"] in result:
            result[row["entity"]]["_revision"] = row["seq"]
    return result


def records(owner, kind, trash=False):
    with database() as conn:
        rows = conn.execute("SELECT * FROM events WHERE owner=? AND kind=? ORDER BY seq", (owner, kind)).fetchall()
    return [value for value in _project(rows).values() if bool(value["deleted_at"]) == trash]


def get_record(owner, kind, entity, trash=False):
    found = next((r for r in records(owner, kind, trash) if r["id"] == entity), None)
    if not found:
        raise HTTPException(404, "记录不存在")
    return found


def append(owner, kind, payload, entity=None, action="create"):
    entity = entity or str(uuid4())
    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("SELECT * FROM events WHERE owner=? AND kind=? AND entity=? ORDER BY seq", (owner, kind, entity)).fetchall()
        previous = _project(rows).get(entity)
        if action == "create" and previous:
            raise HTTPException(409, "记录已存在")
        if action != "create":
            if previous is None:
                raise HTTPException(404, "记录不存在")
            deleted = previous.get("deleted_at")
            if action == "restore":
                if not deleted or now() >= datetime.fromisoformat(deleted)+timedelta(days=30):
                    raise HTTPException(409, "记录未删除或已超过 30 天恢复期限")
            elif deleted:
                raise HTTPException(409, "记录已在回收站")
            if action == "revise" and payload.get("_revision") != previous.get("_revision"):
                raise HTTPException(409, "记录已更新，请刷新后重试")
        conn.execute("INSERT INTO events(owner,kind,entity,action,payload,created) VALUES(?,?,?,?,?,?)", (owner, kind, entity, action, json.dumps(payload, ensure_ascii=False, allow_nan=False), now().isoformat()))
    return entity


def version(owner):
    with database() as conn:
        row = conn.execute("SELECT COALESCE(MAX(seq),0) AS v FROM events WHERE owner=? AND kind='feedback'", (owner,)).fetchone()
    return str(row["v"])
