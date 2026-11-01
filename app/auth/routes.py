from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User

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
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("groups.dashboard"))
    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("groups.dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(
            matric_no=request.form.get("matric_no", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            return redirect(_safe_next(request.args.get("next"))
                            or url_for("groups.dashboard"))
        flash("Wrong matric number or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
