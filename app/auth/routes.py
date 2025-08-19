from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

@auth_bp.get("/login")
def login():
    return render_template("auth/login.html")

@auth_bp.post("/login")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("Invalid credentials", "error")
        return redirect(url_for("auth.login"))
    login_user(user)
    return redirect(url_for("web.dashboard"))

@auth_bp.get("/register")
def register():
    return render_template("auth/register.html")

@auth_bp.post("/register")
def register_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        flash("Email and password required", "error"); return redirect(url_for("auth.register"))
    if User.query.filter_by(email=email).first():
        flash("Email already registered", "error"); return redirect(url_for("auth.register"))
    u = User(email=email); u.set_password(password)
    db.session.add(u); db.session.commit()
    login_user(u)
    return redirect(url_for("web.dashboard"))

@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
