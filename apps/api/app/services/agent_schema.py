"""Versioned, additive migrations; preserve identities and append-only research events."""
import os
import sqlite3
import threading
from datetime import datetime, timezone

_lock=threading.RLock()

def migrate(conn, path):
    with _lock:
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version>=3:return
        if conn.execute('SELECT count(*) FROM users').fetchone()[0]:
            backup=path.parent/'backups';backup.mkdir(exist_ok=True)
            dest=sqlite3.connect(backup/(f'before-v{version+1}-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.sqlite3'))
            try:conn.backup(dest)
            finally:dest.close()
        conn.execute('BEGIN IMMEDIATE')
        try:
            version=conn.execute('PRAGMA user_version').fetchone()[0]
            if version<2:
                cols={r[1] for r in conn.execute('PRAGMA table_info(users)')}
                for name,definition in [('email','TEXT'),('enabled','INTEGER NOT NULL DEFAULT 1'),('bootstrap','INTEGER NOT NULL DEFAULT 0'),('credit_limit','INTEGER NOT NULL DEFAULT 0')]:
                    if name not in cols:conn.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')
                conn.execute('UPDATE users SET bootstrap=1 WHERE username=? AND admin=1',(os.getenv('LASER_ADMIN_USERNAME',''),))
            statements=[
                'CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY,version INTEGER NOT NULL,config TEXT NOT NULL,secret TEXT,updated TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS model_versions(id TEXT,version INTEGER,config TEXT NOT NULL,created TEXT NOT NULL,PRIMARY KEY(id,version))',
                'CREATE TABLE IF NOT EXISTS wallets(owner TEXT PRIMARY KEY,balance INTEGER NOT NULL DEFAULT 0,reserved INTEGER NOT NULL DEFAULT 0)',
                '''CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,kind TEXT NOT NULL,amount INTEGER NOT NULL,reserved_delta INTEGER NOT NULL DEFAULT 0,reference TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(owner,kind,reference))''',
                '''CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,owner TEXT NOT NULL,request_key TEXT NOT NULL,purpose TEXT NOT NULL,fingerprint TEXT NOT NULL,model_id TEXT,price_snapshot TEXT,status TEXT NOT NULL,reserved INTEGER NOT NULL DEFAULT 0,usage TEXT,cost_rmb TEXT,charged INTEGER NOT NULL DEFAULT 0,result TEXT,created TEXT NOT NULL,updated TEXT NOT NULL,UNIQUE(owner,purpose,request_key))''',
                '''CREATE TABLE IF NOT EXISTS codes(id TEXT PRIMARY KEY,hash TEXT UNIQUE NOT NULL,label TEXT NOT NULL,credit INTEGER NOT NULL,total_limit INTEGER NOT NULL,per_user_limit INTEGER NOT NULL,expires TEXT,enabled INTEGER NOT NULL DEFAULT 1,created TEXT NOT NULL)''',
                'CREATE TABLE IF NOT EXISTS redemptions(id INTEGER PRIMARY KEY AUTOINCREMENT,code_id TEXT NOT NULL,owner TEXT NOT NULL,request_key TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(owner,request_key))',
                'CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,action TEXT,entity TEXT,detail TEXT,created TEXT)',
                'CREATE UNIQUE INDEX IF NOT EXISTS unique_email ON users(email) WHERE email IS NOT NULL',
                '''CREATE TABLE IF NOT EXISTS registrations(id TEXT PRIMARY KEY,username TEXT NOT NULL,email TEXT NOT NULL,password TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL,expires TEXT NOT NULL,created TEXT NOT NULL,last_sent TEXT NOT NULL,send_count INTEGER NOT NULL DEFAULT 1,verified TEXT)''',
                'CREATE UNIQUE INDEX IF NOT EXISTS pending_username ON registrations(username) WHERE verified IS NULL',
                'CREATE UNIQUE INDEX IF NOT EXISTS pending_email ON registrations(email) WHERE verified IS NULL',
                '''CREATE TABLE IF NOT EXISTS rate_events(id INTEGER PRIMARY KEY AUTOINCREMENT,scope TEXT NOT NULL,key_hash TEXT NOT NULL,created TEXT NOT NULL)''',
                'CREATE INDEX IF NOT EXISTS rate_events_lookup ON rate_events(scope,key_hash,created)',
                '''CREATE TABLE IF NOT EXISTS work_leases(name TEXT NOT NULL,slot INTEGER NOT NULL,owner TEXT NOT NULL,expires TEXT NOT NULL,PRIMARY KEY(name,slot))''',
            ]
            for sql in statements:conn.execute(sql)
            conn.execute('PRAGMA user_version=3');conn.commit()
        except Exception:conn.rollback();raise
