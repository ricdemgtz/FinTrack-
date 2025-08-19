from datetime import datetime, date
from flask_login import UserMixin
from . import db, login_manager
from passlib.hash import bcrypt

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.password_hash)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # cash|bank|card
    currency = db.Column(db.String(8), default="MXN")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(16), nullable=False)  # expense|income
    color = db.Column(db.String(16), default="#888888")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    pattern = db.Column(db.String(160), nullable=False) # text or regex (prefix re:)
    field = db.Column(db.String(16), default="merchant") # merchant|note
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    min_amount = str  # documentary only; use Numeric in real DBs via SQLAlchemy Numeric
    max_amount = str
    priority = db.Column(db.Integer, default=100)
    active = db.Column(db.Boolean, default=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    merchant = db.Column(db.String(160))
    note = db.Column(db.String(255))
    source = db.Column(db.String(16), default="manual")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transaction.id"))
    filename = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(64))
    size = db.Column(db.Integer)
    sha256 = db.Column(db.String(64), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
