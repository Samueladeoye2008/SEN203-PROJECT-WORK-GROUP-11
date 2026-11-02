import hmac

from flask import Blueprint, current_app, jsonify, request

from .notifications import send_reminders

bp = Blueprint("cron", __name__)


@bp.route("/cron/reminders")
def reminders():
    """Called daily by Vercel Cron, which sends 'Authorization: Bearer <CRON_SECRET>'."""
    secret = current_app.config.get("CRON_SECRET")
    header = request.headers.get("Authorization", "")
    if not secret or not hmac.compare_digest(header, f"Bearer {secret}"):
        return jsonify(error="forbidden"), 403
    return jsonify(sent=send_reminders())
