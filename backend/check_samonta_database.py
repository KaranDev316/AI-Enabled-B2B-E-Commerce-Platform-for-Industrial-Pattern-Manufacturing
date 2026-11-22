"""Read-only compatibility check before applying the integrated migration chain.

Run from backend: .venv/Scripts/python.exe check_samonta_database.py
Never prints URLs/passwords and never stamps, drops, or modifies any table.
"""
from sqlalchemy import create_engine, inspect, text
from app.config import get_settings

REQUIRED = {
    '006': {'quotations','quotation_items','quotation_decisions'},
    '007': {'invoices','order_commercial_snapshots','order_status_events'},
    '008': {'simulated_payments'},
    '009': {'inventory_materials','stock_adjustments'},
    '010': {'production_jobs','job_stage_history'},
    '011': {'production_issues','production_issue_files','production_issue_events'},
}

def check(engine):
    tables=set(inspect(engine).get_table_names())
    with engine.connect() as c:
        revisions=c.execute(text('SELECT version_num FROM alembic_version')).scalars().all() if 'alembic_version' in tables else []
    print('Database revisions:', ', '.join(revisions) if revisions else '(not migrated)')
    if len(revisions)>1 or (revisions and revisions[0] not in [f'{i:03}' for i in range(1,12)]):
        print('STOP: unexpected migration history. Review it before upgrading.');return 2
    rev=int(revisions[0]) if revisions else 0
    missing=set().union(*(t for r,t in REQUIRED.items() if int(r)<=rev)) - tables
    # The old S13/S10 ZIPs also used 006/007, but created different tables.
    ahead=set().union(*(t for r,t in REQUIRED.items() if int(r)>rev)) & tables
    if missing or ahead:
        print('STOP: schema and migration revision do not match the integrated main branch.')
        if missing:print('Missing expected tables:', ', '.join(sorted(missing)))
        if ahead:print('Tables already present ahead of revision:', ', '.join(sorted(ahead)))
        print('Keep this database intact. Back it up and review the old migration files before integrating. Do not stamp head or reset the database.')
        return 2
    print('Compatible migration history. You may run: python -m alembic upgrade head')
    return 0

if __name__=='__main__':
    try:
        url=get_settings().database_url
        if not url:raise ValueError()
        engine=create_engine(url)
        try:code=check(engine)
        finally:engine.dispose()
    except Exception:
        print('STOP: database check could not connect. Check your private backend .env.');code=2
    raise SystemExit(code)
