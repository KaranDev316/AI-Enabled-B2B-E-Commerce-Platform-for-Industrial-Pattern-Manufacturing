"""Opt-in real row-lock races; uses a disposable schema in a localhost *_test DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.quotations import create_draft, update_draft
from app.database import Base
from app.models import RFQ, Quotation, User
from app.schemas.quotation import QuoteCreateInput, QuoteUpdateInput


@pytest.fixture
def pg_engine():
    url = os.getenv('S07_POSTGRES_TEST_URL')
    if not url:
        pytest.skip('Set S07_POSTGRES_TEST_URL to an isolated localhost *_test PostgreSQL database.')
    parsed = make_url(url)
    assert parsed.host in ('localhost', '127.0.0.1') and parsed.database.endswith('_test')
    schema = 's07_' + uuid4().hex
    root = create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        root.dispose()


@pytest.mark.parametrize('prior_version,prior_status', [(0, 'draft'), (1, 'draft'), (1, 'rejected')])
def test_simultaneous_versions_are_serialized(pg_engine, prior_version, prior_status):
    with Session(pg_engine) as db:
        user = User(email='admin@s07.test', password_hash='test-only', role='admin', is_active=True)
        db.add(user); db.flush()
        rfq = RFQ(rfq_number='RFQ-PG', customer_id=user.id, title='Tooling', material='Wood', quantity=1)
        db.add(rfq); db.commit()
        user_id, rfq_id = user.id, rfq.id
        if prior_version:
            create_draft(rfq_id, QuoteCreateInput(expected_version=0), user, db)
            if prior_status == 'rejected':
                db.scalar(select(Quotation)).status = 'rejected'
                db.get(RFQ, rfq_id).status = 'rejected'
                db.commit()
    barrier = Barrier(2)

    def attempt():
        with Session(pg_engine) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                result = create_draft(rfq_id, QuoteCreateInput(expected_version=prior_version), user, db)
                return 201, result['version']
            except HTTPException as exc:
                return exc.status_code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(status for status, _ in results) == [201, 409]
    with Session(pg_engine) as db:
        quotes = list(db.scalars(select(Quotation).order_by(Quotation.version)))
        assert len(quotes) == prior_version + 1
        assert quotes[-1].version == prior_version + 1 and quotes[-1].status == 'draft'
        if prior_version:
            assert quotes[0].status == ('rejected' if prior_status == 'rejected' else 'superseded')


def test_failed_revision_rolls_back_reopening_and_preserves_rejected_offer(pg_engine):
    with Session(pg_engine) as db:
        user = User(email='rollback@s07.test', password_hash='fixture-only', role='admin', is_active=True)
        db.add(user); db.flush()
        rfq = RFQ(rfq_number='RFQ-ROLLBACK', customer_id=user.id, title='Tooling', material='Wood', quantity=1)
        db.add(rfq); db.commit()
        rfq_id = rfq.id
        first = create_draft(rfq_id, QuoteCreateInput(expected_version=0), user, db)
        db.get(Quotation, first['id']).status = 'rejected'
        db.get(RFQ, rfq_id).status = 'rejected'
        db.commit()
        def fail_insert(*_args):
            raise IntegrityError('injected revision failure', {}, Exception('test failure'))
        event.listen(Quotation, 'before_insert', fail_insert)
        try:
            with pytest.raises(HTTPException) as failure:
                create_draft(rfq_id, QuoteCreateInput(expected_version=1), user, db)
            assert failure.value.status_code == 409
        finally:
            event.remove(Quotation, 'before_insert', fail_insert)
        db.expire_all()
        assert db.get(RFQ, rfq_id).status == 'rejected'
        assert len(list(db.scalars(select(Quotation)))) == 1
        assert db.get(Quotation, first['id']).status == 'rejected'


def test_simultaneous_draft_edits_do_not_overwrite(pg_engine):
    with Session(pg_engine) as db:
        user = User(email='admin@s07.test', password_hash='test-only', role='admin', is_active=True)
        db.add(user); db.flush()
        rfq = RFQ(rfq_number='RFQ-PG', customer_id=user.id, title='Tooling', material='Wood', quantity=1)
        db.add(rfq); db.commit()
        user_id = user.id
        quote_id = create_draft(rfq.id, QuoteCreateInput(expected_version=0), user, db)['id']
    barrier = Barrier(2)

    def attempt(note):
        with Session(pg_engine) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                update_draft(quote_id, QuoteUpdateInput(expected_revision=1, notes=note), user, db)
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ['First', 'Second'])) == [200, 409]
    with Session(pg_engine) as db:
        assert db.get(Quotation, quote_id).revision == 2
