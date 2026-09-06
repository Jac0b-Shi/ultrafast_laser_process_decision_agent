"""Docker: python /workspace/scripts/backup_agent.py; keep DB and encryption key together."""
import hashlib
import json
import shutil
from app.services import agent_store as store
from app.settings import get_settings
import sqlite3

root=get_settings().experiments_dir/'agent'
destination=root/'backups'/('snapshot-'+store.now().strftime('%Y%m%dT%H%M%S%f'))
destination.mkdir(parents=True)
with store.database() as conn:
    target=sqlite3.connect(destination/'state.sqlite3')
    try:conn.backup(target)
    finally:target.close()
for name in ('secrets','blobs'):
    if (root/name).exists():shutil.copytree(root/name,destination/name)
manifest={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
(destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(destination)
