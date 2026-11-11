from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from .. import limits
from ..extensions import db
from ..models import User
from ..notifications import notify_reset, notify_welcome
from ..tokens import read_reset_token
from ..mailer import config_problem

bp = Blueprint("auth", __name__)


def _safe_next(target):
    """Allow only local redirects (prevents open-redirect attacks)."""
    return target if target and target.startswith("/") and not target.startswith("//") else None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("groups.dashboard"))
    form = request.form
    if request.method == "POST":
        name = form.get("name", "").strip()
        matric = form.get("matric_no", "").strip()
        email = form.get("email", "").strip().lower()
        pw, pw2 = form.get("password", ""), form.get("confirm", "")
        errors = []
        if not limits.get_limit("registration_open"):
            errors.append("Registration is currently closed.")
        if limits.over(limits.get_limit("max_users"), User.query.count()):
            errors.append("The system has reached its user limit.")
        if limits.storage_full():
            errors.append(limits.STORAGE_MSG)
        if not name:
            errors.append("Name is required.")
        if not matric:
            errors.append("Matric number is required.")
        if "@" not in email:
            errors.append("Enter a valid email.")
        if len(pw) < 8:
            errors.append("Password must be at least 8 characters.")
        if pw != pw2:
            errors.append("Passwords do not match.")
        if matric and User.query.filter_by(matric_no=matric).first():
            errors.append("That matric number is already registered.")
        if email and User.query.filter_by(email=email).first():
            errors.append("That email is already registered.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=form)
        user = User(name=name, matric_no=matric, email=email)
        user.set_password(pw)
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Registration database error")
            flash("We could not create your account because the database could not complete the request. Please try again.", "error")
            return render_template("register.html", form=form), 500

        # Email is deliberately after the successful transaction and is already
        # implemented as a non-raising best-effort operation. Registration must
        # never be rolled back because the optional email relay is unavailable.
        try:
            notify_welcome(user)
        except Exception:
            current_app.logger.exception("Welcome email failed after registration")
        return redirect(url_for("groups.dashboard"))
    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("groups.dashboard"))
    if request.method == "POST":
        try:
            identifier = request.form.get("matric_no", "").strip()
            user = User.query.filter_by(matric_no=identifier).first()
            if not user and "@" in identifier:
                user = User.query.filter_by(email=identifier.lower()).first()
            if user and user.check_password(request.form.get("password", "")):
                if not user.is_active:
                    flash("This account is suspended. Contact the administrator.", "error")
                    return render_template("login.html")
                login_user(user)
                return redirect(_safe_next(request.args.get("next"))
                                or url_for("groups.dashboard"))
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Login database error")
            flash("We could not sign you in because the database could not complete the request. Please try again.", "error")
            return render_template("login.html"), 500
        flash("Wrong matric number or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        cur, new, new2 = (request.form.get(k, "") for k in ("current", "new", "confirm"))
        if not current_user.check_password(cur):
            flash("Current password is wrong.", "error")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new != new2:
            flash("New passwords do not match.", "error")
        else:
            try:
                current_user.set_password(new)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Password change database error")
                flash("We could not change your password. Please try again.", "error")
            else:
                flash("Password changed.", "message")
                return redirect(url_for("auth.account"))
    return render_template("account.html")


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if config_problem(current_app):
            flash("Email is not set up on this system. Ask an administrator to reset your password.", "error")
            return render_template("forgot.html")
        user = User.query.filter_by(email=email).first() if email else None
        # At most 3 reset emails per address per day. Same answer either way (no account guessing).
        if user and user.is_active and limits.bump(f"reset:{email}:{limits.today()}") <= 3:
            notify_reset(user)
        flash("If that email is registered, a reset link is on its way. Check your spam folder too.", "message")
        return redirect(url_for("auth.login"))
    return render_template("forgot.html")


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = read_reset_token(token)
    if not user:
        flash("That reset link is invalid or has expired. Request a new one.", "error")
        return redirect(url_for("auth.forgot"))
    if request.method == "POST":
        new, new2 = request.form.get("new", ""), request.form.get("confirm", "")
        if len(new) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif new != new2:
            flash("Passwords do not match.", "error")
        else:
            try:
                user.set_password(new)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Password reset database error")
                flash("We could not update your password. Please request a new reset link.", "error")
            else:
                flash("Password updated. You can log in now.", "message")
                return redirect(url_for("auth.login"))
    return render_template("reset.html", token=token)
