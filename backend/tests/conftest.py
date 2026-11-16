from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import create_app
from app.models import CustomerProfile, EmployeeProfile, User, UserRole
from app.services.security import hash_password


@pytest.fixture(scope='session')
def test_db_engine():
    # Use SQLite in-memory with StaticPool for fast, isolated, zero-external-dependency test runs
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine) -> Generator[Session, None, None]:
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def app_instance(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app_instance) -> TestClient:
    return TestClient(app_instance, base_url='http://127.0.0.1:8000')


@pytest.fixture
def test_users(db_session) -> dict[str, User]:
    """Provisions standard test fixtures (U-C1, U-E1, U-A1, U-OFF) per VERIFICATION_PLAN.md."""
    # U-C1: Active Customer with Profile
    u_c1 = User(
        email='customer.one@example.test',
        password_hash=hash_password('Customer@12345'),
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )
    db_session.add(u_c1)
    db_session.flush()

    c1_profile = CustomerProfile(
        user_id=u_c1.id,
        company_name='Apex Castings Ltd',
        contact_person='Rajesh Patel',
        phone='+919876543210',
        gstin='24AAACA1234A1Z5',
        address='Plot 12, GIDC Vatva, Ahmedabad',
    )
    db_session.add(c1_profile)

    # U-C2: Second active Customer
    u_c2 = User(
        email='customer.two@example.test',
        password_hash=hash_password('Customer@12345'),
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )
    db_session.add(u_c2)
    db_session.flush()

    c2_profile = CustomerProfile(
        user_id=u_c2.id,
        company_name='Gujarat Forgings Ltd',
        contact_person='Suresh Shah',
        phone='+919876543211',
    )
    db_session.add(c2_profile)

    # U-E1: Active Employee with Profile
    u_e1 = User(
        email='employee.one@example.test',
        password_hash=hash_password('Employee@12345'),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
    )
    db_session.add(u_e1)
    db_session.flush()

    e1_profile = EmployeeProfile(
        user_id=u_e1.id,
        full_name='Vikram Sharma',
        phone='+919876543212',
        department='Machining & Tooling',
    )
    db_session.add(e1_profile)

    # U-A1: Active Admin
    u_a1 = User(
        email='admin.one@example.test',
        password_hash=hash_password('Admin@12345'),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add(u_a1)

    # U-OFF: Deactivated account with valid credentials
    u_off = User(
        email='inactive.user@example.test',
        password_hash=hash_password('Inactive@12345'),
        role=UserRole.CUSTOMER.value,
        is_active=False,
    )
    db_session.add(u_off)

    db_session.commit()

    return {
        'customer_1': u_c1,
        'customer_2': u_c2,
        'employee_1': u_e1,
        'admin_1': u_a1,
        'inactive': u_off,
    }
