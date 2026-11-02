"""Send email through a Google Apps Script web app (free Gmail quota)."""
import json
import logging
import urllib.request

log = logging.getLogger(__name__)
ALLOWED_PREFIX = "https://script.google.com/"


def send_email(app, to, subject, body):
    """Return True if the relay accepted the message. Never raises."""
    url = app.config.get("APPS_SCRIPT_URL")
    secret = app.config.get("APPS_SCRIPT_SECRET")
    # Only ever send the secret to Google, even if the URL is mistyped.
    if not (url and secret and to and url.startswith(ALLOWED_PREFIX)):
        return False
    payload = json.dumps({"secret": secret, "to": to,
                          "subject": subject[:150], "body": body[:3000]}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return bool(json.loads(resp.read().decode()).get("ok"))
    except Exception as exc:                       # network, timeout, bad JSON
        log.warning("Email failed: %s", type(exc).__name__)
        return False
