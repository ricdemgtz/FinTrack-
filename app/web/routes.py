from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .. import db
from ..models import Transaction, Account, Category

web_bp = Blueprint("web", __name__)

@web_bp.get("/")
def home():
    return redirect(url_for("web.dashboard"))

@web_bp.get("/dashboard")
@login_required
def dashboard():
    # Minimal dashboard data
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(10).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    total = sum([float(t.amount) for t in txs]) if txs else 0.0
    return render_template("dashboard.html", recent=txs, total=total, accounts=accounts, categories=categories)

@web_bp.get("/upload")
@login_required
def upload_page():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template("upload.html", accounts=accounts)
