import sys
from pathlib import Path
from alembic import context
from sqlalchemy import create_engine, pool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import get_settings
from app.database import Base
import app.models  # Registers models on Base.metadata

target_metadata = Base.metadata
url = get_settings().database_url
if not url:
    raise RuntimeError('Configure a DATABASE_URL before running Alembic.')

is_sqlite = url.startswith('sqlite:///')
if not is_sqlite and not (url.startswith('postgresql+psycopg://') or url.startswith('postgresql://')):
    raise RuntimeError('DATABASE_URL must use postgresql+psycopg:// or sqlite:/// scheme.')

if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=is_sqlite,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    connect_args = {'check_same_thread': False} if is_sqlite else {}
    poolclass = pool.StaticPool if is_sqlite else pool.NullPool
    engine = create_engine(url, poolclass=poolclass, connect_args=connect_args)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
