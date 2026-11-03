"""Name shown across the app: admin-editable, falling back to APP_NAME in config."""
from flask import current_app

from . import limits
from .extensions import db


def app_name():
    try:
        return limits.get_text("app_name", current_app.config["APP_NAME"])
    except Exception:                       # e.g. tables not created yet
        db.session.rollback()
        return current_app.config["APP_NAME"]
