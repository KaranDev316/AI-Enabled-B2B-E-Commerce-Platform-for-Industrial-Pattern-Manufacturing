import argparse
import sys

from app.database import get_db
from app.models import User, UserRole
from app.services.security import hash_password


def create_admin_user(email: str, password: str) -> User:
    """Provisions or updates the initial Admin account with an Argon2id password hash."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = UserRole.ADMIN.value
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            print(f'Admin user updated: {email}')
            return existing
        else:
            admin = User(
                email=email.lower().strip(),
                password_hash=hash_password(password),
                role=UserRole.ADMIN.value,
                is_active=True,
                must_change_password=False,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f'Admin user created successfully: {email}')
            return admin
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='KPC Administrative CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    admin_parser = subparsers.add_parser('create-admin', help='Provision an initial Admin user')
    admin_parser.add_argument('--email', required=True, help='Admin email address')
    admin_parser.add_argument('--password', required=True, help='Admin plaintext password')

    args = parser.parse_args()
    if args.command == 'create-admin':
        create_admin_user(args.email, args.password)


if __name__ == '__main__':
    main()
