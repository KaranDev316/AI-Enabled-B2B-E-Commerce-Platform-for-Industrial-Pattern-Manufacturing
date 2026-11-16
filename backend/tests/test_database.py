import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.mark.database
def test_postgresql_connection():
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set isolated TEST_DATABASE_URL for the PostgreSQL connection check.')
    parsed = make_url(url)
    assert parsed.drivername == 'postgresql+psycopg'
    assert parsed.database and parsed.database.endswith('_test'), 'Use a dedicated *_test database.'
    configured_app = os.getenv('DATABASE_URL')
    if configured_app:
        app_url = make_url(configured_app)
        assert (parsed.host, parsed.port, parsed.database) != (app_url.host, app_url.port, app_url.database)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text('SELECT 1')).scalar_one() == 1
    finally:
        engine.dispose()
