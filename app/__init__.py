"""Application factory."""
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from config import Config
from .db_select import pick_database
import os

from . import branding, limits
from .extensions import db, login_manager, csrf


def create_app(config=Config):
    # Static files live in public/static so Vercel's CDN serves them in production.
    app = Flask(__name__, static_folder="../public/static", static_url_path="/static")
    app.config.from_object(config)

    pick_database(app)          # Neon if reachable, else SQLite backup
    if os.environ.get("VERCEL"):         # trust Vercel's proxy headers so email links use https
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "error"

    from .auth.routes import bp as auth_bp
    from .groups.routes import bp as groups_bp
    from .tasks.routes import bp as tasks_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(tasks_bp)
    from .cron import bp as cron_bp
    from .admin.routes import bp as admin_bp
    app.register_blueprint(cron_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def throttle_writes():
        """Daily cap on write requests (POST) per user; admins are exempt."""
        if (request.method != "POST" or not current_user.is_authenticated
                or current_user.is_superadmin):
            return None
        used = limits.bump(f"writes:{current_user.id}:{limits.today()}")
        cap = limits.get_limit("daily_writes_per_user")
        if cap > 0 and used > cap:
            msg = "Daily request limit reached. Try again tomorrow."
            if request.is_json:
                return jsonify(error=msg), 429
            flash(msg, "error")
            return redirect(url_for("groups.dashboard"))
        return None

    @app.context_processor
    def inject_app_name():
        return {"app_name": branding.app_name()}

    @app.route("/")
    def index():
        """Landing page for visitors; signed-in users go straight to their boards."""
        if current_user.is_authenticated:
            return redirect(url_for("groups.dashboard"))
        return render_template("landing.html")

    with app.app_context():
        db.create_all()
        from .schema import ensure_columns
        ensure_columns()
    return app
