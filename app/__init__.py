"""Application factory."""
from flask import Flask, redirect, url_for
from config import Config
from .db_select import pick_database
from .extensions import db, login_manager, csrf


def create_app(config=Config):
    # Static files live in public/static so Vercel's CDN serves them in production.
    app = Flask(__name__, static_folder="../public/static", static_url_path="/static")
    app.config.from_object(config)

    pick_database(app)          # Neon if reachable, else SQLite backup
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
    app.register_blueprint(cron_bp)

    @app.route("/")
    def index():
        return redirect(url_for("groups.dashboard"))

    with app.app_context():
        db.create_all()
    return app
