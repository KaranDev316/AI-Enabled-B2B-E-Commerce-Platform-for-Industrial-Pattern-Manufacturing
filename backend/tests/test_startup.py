"""The deployment entry point must migrate successfully before it starts serving."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
import start


def test_migration_failure_never_starts_server(monkeypatch):
    def fail():
        raise RuntimeError('Migration failed')
    monkeypatch.setattr(start, 'migrate', fail)
    monkeypatch.setattr(start.os, 'chdir', lambda path: None)
    monkeypatch.setattr(start.os, 'execv', lambda *args: pytest.fail('Server must not start after a failed migration'))
    with pytest.raises(RuntimeError, match='Migration failed'):
        start.main([])


def test_migrate_then_server_uses_configured_port_and_exec(monkeypatch):
    calls=[]
    monkeypatch.setattr(start, 'migrate', lambda: calls.append('migrated'))
    monkeypatch.setattr(start.os, 'chdir', lambda path: None)
    def execute(executable, arguments):
        assert calls==['migrated']
        assert arguments[1:4]==['-m','uvicorn','app.main:app']
        assert arguments[-4:]==['--host','0.0.0.0','--port','12345']
        calls.append('server')
    monkeypatch.setattr(start.os, 'execv', execute)
    start.main(['--host','0.0.0.0','--port','12345'])
    assert calls==['migrated','server']


def test_repeated_migration_startup_is_idempotent(tmp_path):
    backend=Path(__file__).resolve().parents[1]
    url=f'sqlite:///{tmp_path / "startup.db"}'
    env={**os.environ,'DATABASE_URL':url}
    for _ in range(2):
        subprocess.run([sys.executable,str(backend/'start.py'),'--migrate-only'],cwd=backend.parent,env=env,check=True,capture_output=True,stdin=subprocess.DEVNULL)
    scripts=ScriptDirectory.from_config(Config(str(backend/'alembic.ini')))
    engine=create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()==scripts.get_current_head()
    engine.dispose()


def test_concurrent_postgresql_startups_apply_migrations_once():
    from concurrent.futures import ThreadPoolExecutor
    from uuid import uuid4
    from sqlalchemy.engine import make_url
    raw=os.getenv('S07_POSTGRES_TEST_URL')
    if not raw:
        pytest.skip('Set S07_POSTGRES_TEST_URL to a dedicated localhost *_test database.')
    url=make_url(raw)
    assert url.host in ('127.0.0.1','localhost') and url.database.endswith('_test')
    schema='startup_'+uuid4().hex
    root=create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    scoped=url.set(query={**url.query,'options':f'-csearch_path={schema}'})
    env={**os.environ,'DATABASE_URL':scoped.render_as_string(hide_password=False)}
    backend=Path(__file__).resolve().parents[1]
    engine=create_engine(scoped)
    try:
        def launch(_):
            return subprocess.run([sys.executable,str(backend/'start.py'),'--migrate-only'],cwd=backend.parent,env=env,check=True,capture_output=True,timeout=45,stdin=subprocess.DEVNULL)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(launch,range(2)))
        scripts=ScriptDirectory.from_config(Config(str(backend/'alembic.ini')))
        with engine.connect() as conn:
            assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()==scripts.get_current_head()
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        root.dispose()
