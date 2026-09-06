"""Administrator-owned SMTP settings and verified public registration."""
from __future__ import annotations

import hashlib
import json
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException

from app.services import agent_store as store
from app.services.agent_model_config import cipher


DEFAULTS = {
    "enabled": False,
    "host": "smtp.feishu.cn",
    "port": 465,
    "security": "ssl",
    "username": "no-reply@jac0bshi.cn",
    "sender_email": "no-reply@jac0bshi.cn",
    "sender_name": "超快激光加工工艺数据库智能体",
    "public_base_url": "https://laser.jac0bshi.cn",
    "verification_ttl_minutes": 30,
}


def _setting(conn, key):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def config(include_secret=False):
    with store.database() as conn:
        raw = _setting(conn, "email_config")
        encrypted = _setting(conn, "email_secret")
    result = {**DEFAULTS, **(json.loads(raw) if raw else {})}
    result["has_password"] = bool(encrypted)
    if include_secret:
        result["password"] = cipher().decrypt(encrypted.encode()).decode() if encrypted else ""
    return result


def _clean(body):
    result = {**DEFAULTS, **{k: body[k] for k in DEFAULTS if k in body}}
    if not isinstance(result["enabled"], bool):
        raise HTTPException(422, "邮箱注册启停设置无效")
    for key in ("host", "username", "sender_email", "sender_name", "public_base_url"):
        value = result[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 254 or "\r" in value or "\n" in value:
            raise HTTPException(422, "邮件配置格式无效")
        result[key] = value.strip()
    result["sender_email"] = store.normalize_email(result["sender_email"])
    if "@" in result["username"]:
        store.normalize_email(result["username"])
    url = urlparse(result["public_base_url"])
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise HTTPException(422, "公开访问地址必须是无凭据的 HTTP(S) 地址")
    result["public_base_url"] = result["public_base_url"].rstrip("/")
    if result["security"] not in ("ssl", "starttls"):
        raise HTTPException(422, "SMTP 安全方式无效")
    if isinstance(result["port"], bool) or not isinstance(result["port"], int) or not 1 <= result["port"] <= 65535:
        raise HTTPException(422, "SMTP 端口无效")
    ttl = result["verification_ttl_minutes"]
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 5 <= ttl <= 1440:
        raise HTTPException(422, "验证链接有效期须为 5–1440 分钟")
    return result


def save(body, actor):
    cleaned = _clean(body)
    password = body.get("password")
    if password is not None and (not isinstance(password, str) or len(password) > 8192):
        raise HTTPException(422, "SMTP 专用密码格式无效")
    with store.database() as conn:
        prior = _setting(conn, "email_secret")
        encrypted = cipher().encrypt(password.encode()).decode() if password else prior
        if body.get("clear_password"):
            encrypted = None
        if cleaned["enabled"] and not encrypted:
            raise HTTPException(422, "启用邮箱注册前请配置 SMTP 专用密码")
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('email_config',?)", (json.dumps(cleaned, ensure_ascii=False),))
        if encrypted:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('email_secret',?)", (encrypted,))
        else:
            conn.execute("DELETE FROM settings WHERE key='email_secret'")
        conn.execute("INSERT INTO admin_audit(actor,action,entity,detail,created) VALUES(?,?,?,?,?)", (actor, "email.save", "smtp", json.dumps(cleaned, ensure_ascii=False), store.now().isoformat()))
    return {**cleaned, "has_password": bool(encrypted)}


def _send(recipient, subject, text):
    cfg = config(True)
    if not cfg["password"]:
        raise HTTPException(503, "SMTP 专用密码尚未配置")
    message = EmailMessage()
    recipient = store.normalize_email(recipient)
    if not recipient:
        raise HTTPException(422, "请填写测试收件邮箱")
    message["From"] = f'{cfg["sender_name"]} <{cfg["sender_email"]}>'
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    context = ssl.create_default_context()
    try:
        if cfg["security"] == "ssl":
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20, context=context) as smtp:
                smtp.login(cfg["username"], cfg["password"])
                smtp.send_message(message)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
                smtp.starttls(context=context)
                smtp.login(cfg["username"], cfg["password"])
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(502, "邮件发送失败，请管理员检查 SMTP 配置") from exc


def send_test(recipient):
    _send(recipient, "超快激光智能体邮件配置测试", "这是一封 SMTP 配置测试邮件。收到此邮件表示发信配置可用。")


def register(username, email, password, request):
    from app.services import rate_limit
    cfg = config()
    if not cfg["enabled"]:
        raise HTTPException(503, "邮箱注册暂未开放")
    username = username.strip()
    email = store.normalize_email(email)
    if not email:
        raise HTTPException(422, "请填写有效邮箱")
    if not 1 <= len(username) <= 80 or not 12 <= len(password) <= 256:
        raise HTTPException(422, "用户名不能为空，密码须为 12–256 字符")
    rate_limit.consume("registration.ip", rate_limit.client_key(request), ((3600,10),(86400,30)))
    instant = store.now()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    registration_id = str(uuid4())
    generic = {"ok": True, "message": "如果信息可用于注册，验证邮件将很快送达。"}
    with store.database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM registrations WHERE verified IS NULL AND expires<=?", (instant.isoformat(),))
        if conn.execute("SELECT 1 FROM users WHERE username=? OR email=?", (username, email)).fetchone():
            return generic
        matches = conn.execute("SELECT * FROM registrations WHERE verified IS NULL AND (username=? OR email=?) ORDER BY created DESC", (username, email)).fetchall()
        if len(matches) > 1:
            return generic
        prior = matches[0] if len(matches) == 1 else None
        if prior:
            last_sent = datetime.fromisoformat(prior["last_sent"])
            created = datetime.fromisoformat(prior["created"])
            if instant-last_sent < timedelta(seconds=60) or (instant-created < timedelta(hours=1) and prior["send_count"] >= 3):
                return generic
            registration_id = prior["id"]
            count = prior["send_count"] + 1 if instant-created < timedelta(hours=1) else 1
            conn.execute("UPDATE registrations SET username=?,email=?,password=?,token_hash=?,expires=?,created=?,last_sent=?,send_count=? WHERE id=?", (username,email,store.password_hash(password),token_hash,(instant+timedelta(minutes=cfg["verification_ttl_minutes"])).isoformat(),created.isoformat() if count>1 else instant.isoformat(),instant.isoformat(),count,registration_id))
        else:
            conn.execute("INSERT INTO registrations VALUES(?,?,?,?,?,?,?,?,?,NULL)", (registration_id,username,email,store.password_hash(password),token_hash,(instant+timedelta(minutes=cfg["verification_ttl_minutes"])).isoformat(),instant.isoformat(),instant.isoformat(),1))
    try:
        link = f'{cfg["public_base_url"]}/verify?token={token}'
        _send(email, "验证你的超快激光智能体账号", f"你好，{username}：\n\n请打开以下链接完成邮箱验证：\n{link}\n\n链接将在 {cfg['verification_ttl_minutes']} 分钟后失效。若不是你本人操作，请忽略此邮件。")
    except Exception:
        with store.database() as conn:
            conn.execute("DELETE FROM registrations WHERE id=? AND token_hash=?", (registration_id, token_hash))
        raise
    return generic


def verify(token):
    if not isinstance(token, str) or not 20 <= len(token) <= 200:
        raise HTTPException(422, "验证链接无效")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with store.database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM registrations WHERE token_hash=? AND verified IS NULL AND expires>?", (digest, store.now().isoformat())).fetchone()
        if not row:
            raise HTTPException(409, "验证链接无效或已过期")
        if conn.execute("SELECT 1 FROM users WHERE username=? OR email=?", (row["username"], row["email"])).fetchone():
            raise HTTPException(409, "用户名或邮箱已被使用")
        user_id = str(uuid4())
        conn.execute("INSERT INTO users(id,username,password,admin,email,enabled,bootstrap,credit_limit) VALUES(?,?,?,?,?,?,?,?)", (user_id,row["username"],row["password"],0,row["email"],1,0,0))
        conn.execute("DELETE FROM registrations WHERE id=?", (row["id"],))
        conn.execute("INSERT INTO admin_audit(actor,action,entity,detail,created) VALUES(?,?,?,?,?)", (user_id,"registration.verify",user_id,json.dumps({"username":row["username"],"email":row["email"]},ensure_ascii=False),store.now().isoformat()))
    return {"ok": True, "username": row["username"]}
