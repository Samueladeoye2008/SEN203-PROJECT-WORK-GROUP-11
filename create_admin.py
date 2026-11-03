"""Create or promote the super admin. Run locally: python create_admin.py
For the hosted (Neon) database set DATABASE_URL in this terminal first (see README)."""
import getpass

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
with app.app_context():
    name = input("Full name: ").strip()
    matric = input("Admin ID (used to log in): ").strip()
    email = input("Email: ").strip().lower()
    pw = getpass.getpass("Password (min 10 characters): ")
    if len(pw) < 10 or pw != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords must match and be at least 10 characters.")
    user = User.query.filter_by(matric_no=matric).first()
    if user:
        print("Existing user found: promoting to super admin and resetting password.")
    else:
        if not (name and email and matric):
            raise SystemExit("Name, ID and email are required.")
        user = User(name=name, matric_no=matric, email=email)
        db.session.add(user)
    user.set_password(pw)
    user.is_active = True
    user.is_superadmin = True
    db.session.commit()
    print("Super admin ready. Log in at /login, then open /admin.")
