"""Signed, expiring, single-use password reset tokens."""
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .extensions import db
from .models import User


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def make_reset_token(user):
    # The password-hash tail changes once the password changes, so a link works only once.
    return _serializer().dumps({"id": user.id, "h": user.password_hash[-12:]})


def read_reset_token(token, max_age=3600):
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(User, data.get("id"))
    if user and user.is_active and user.password_hash[-12:] == data.get("h"):
        return user
    return None
