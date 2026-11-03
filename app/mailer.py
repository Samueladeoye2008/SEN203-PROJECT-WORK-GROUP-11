"""Send email through a Google Apps Script web app (free Gmail quota)."""
import json
import logging
import urllib.error
import urllib.request

from . import limits

log = logging.getLogger(__name__)
ALLOWED_PREFIX = "https://script.google.com/"


def config_problem(app):
    """Return a plain-English reason email cannot work, or '' if configured."""
    url = app.config.get("APPS_SCRIPT_URL")
    if not url:
        return "APPS_SCRIPT_URL is empty. Put it in the .env file (not .env.example) and restart the server."
    if not app.config.get("APPS_SCRIPT_SECRET"):
        return "APPS_SCRIPT_SECRET is empty. It must equal SHARED_SECRET in the Apps Script project."
    if not url.startswith(ALLOWED_PREFIX):
        return "APPS_SCRIPT_URL must start with https://script.google.com/ and end with /exec."
    return ""


def send_email_detailed(app, to, subject, body, html=None):
    """Return (ok, reason). Never raises."""
    problem = config_problem(app)
    if problem or not to:
        return False, problem or "No recipient address."
    if not limits.get_limit("emails_enabled"):
        return False, "Email notifications are switched off in admin Limits."
    day_key = f"email:{limits.today()}"
    if limits.over(limits.get_limit("daily_emails"), limits.count(day_key)):
        log.warning("Daily email cap reached.")
        return False, "Daily email cap reached."
    payload = json.dumps({"secret": app.config["APPS_SCRIPT_SECRET"], "to": to,
                          "subject": subject[:150], "body": body[:3000],
                          "html": (html or "")[:20000]}).encode()
    req = urllib.request.Request(app.config["APPS_SCRIPT_URL"], data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return False, (f"Google answered HTTP {exc.code}. Check the URL is the /exec Web app URL "
                       "and that access is set to Anyone.")
    except Exception as exc:                       # network, timeout
        log.warning("Email failed: %s", type(exc).__name__)
        return False, f"Could not reach Google ({type(exc).__name__}). Check your internet connection."
    try:
        data = json.loads(raw)
    except ValueError:
        return False, ("Google did not return JSON. The URL is wrong, or the deployment is not set to "
                       "Execute as Me / Access Anyone.")
    if data.get("ok"):
        limits.bump(day_key)
        return True, "sent"
    err = data.get("error", "unknown")
    if err == "unauthorized":
        return False, "The script rejected the secret. APPS_SCRIPT_SECRET must equal SHARED_SECRET exactly."
    return False, f"The script reported: {err}"


def send_email(app, to, subject, body, html=None):
    """Return True if the relay accepted the message. Never raises."""
    return send_email_detailed(app, to, subject, body, html)[0]
