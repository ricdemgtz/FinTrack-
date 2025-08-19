from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, hashlib
from datetime import date, datetime
from .. import db
from ..models import Transaction, Attachment, Account, Category, Rule
from ..ocr import extract_fields

api_bp = Blueprint("api", __name__)

def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())


def _success(data=None, message=None, status=200):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return jsonify(payload), status


def _error(message, status=400, errors=None):
    payload = {"success": False, "message": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status

@api_bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    account_id = request.form.get("account_id", type=int)
    if not f or not account_id:
        return jsonify({"error": "file and account_id are required"}), 400
    if not _allowed(f.filename):
        return jsonify({"error": "file type not allowed"}), 400

    data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    updir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(updir, exist_ok=True)
    name = f"{sha}_{secure_filename(f.filename)}"
    path = os.path.join(updir, name)
    if not os.path.exists(path):
        with open(path, "wb") as out:
            out.write(data)

    fields = extract_fields(path)

    tx = Transaction(
        user_id=current_user.id,
        account_id=account_id,
        date=fields.get("date", date.today()),
        amount=fields.get("amount", 0),
        merchant=fields.get("merchant", ""),
        note="(OCR)",
        source="ocr"
    )
    db.session.add(tx); db.session.commit()

    att = Attachment(
        user_id=current_user.id,
        transaction_id=tx.id,
        filename=name,
        mime=f.mimetype,
        size=len(data),
        sha256=sha
    )
    db.session.add(att); db.session.commit()
    return jsonify({"ok": True, "transaction_id": tx.id, "attachment_id": att.id})


# --- Accounts CRUD ---

def _account_to_dict(a: Account):
    return {"id": a.id, "name": a.name, "type": a.type, "currency": a.currency}


@api_bp.get("/accounts")
@login_required
def accounts_list():
    items = (
        Account.query.filter_by(user_id=current_user.id)
        .filter(Account.deleted_at.is_(None))
        .all()
    )
    return _success([_account_to_dict(a) for a in items])


@api_bp.post("/accounts")
@login_required
def accounts_create():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    acc_type = data.get("type")
    currency = data.get("currency", "MXN")
    if not name or not (1 <= len(name) <= 80):
        return _error("invalid name", errors={"name": ["required or length"]})
    if not acc_type:
        return _error("name and type required")
    exists = (
        Account.query.filter(Account.user_id == current_user.id)
        .filter(db.func.lower(Account.name) == name.lower())
        .filter(Account.deleted_at.is_(None))
        .first()
    )
    if exists:
        return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    a = Account(user_id=current_user.id, name=name, type=acc_type, currency=currency)
    db.session.add(a); db.session.commit()
    return _success(_account_to_dict(a), status=201)


def _get_account(id: int, include_deleted=False):
    q = Account.query.filter_by(id=id, user_id=current_user.id)
    if not include_deleted:
        q = q.filter(Account.deleted_at.is_(None))
    return q.first_or_404()


@api_bp.get("/accounts/<int:id>")
@login_required
def accounts_get(id):
    a = _get_account(id)
    return _success(_account_to_dict(a))


@api_bp.put("/accounts/<int:id>")
@login_required
def accounts_update(id):
    a = _get_account(id)
    data = request.get_json() or {}
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name or not (1 <= len(name) <= 80):
            return _error("invalid name", errors={"name": ["required or length"]})
        exists = (
            Account.query.filter(Account.user_id == current_user.id)
            .filter(db.func.lower(Account.name) == name.lower())
            .filter(Account.id != id)
            .filter(Account.deleted_at.is_(None))
            .first()
        )
        if exists:
            return _error("duplicate account name", status=409, errors={"name": ["exists"]})
        data["name"] = name
    for field in ["name", "type", "currency"]:
        if field in data:
            setattr(a, field, data[field])
    db.session.commit()
    return _success(_account_to_dict(a))


@api_bp.delete("/accounts/<int:id>")
@login_required
def accounts_delete(id):
    a = _get_account(id)
    a.deleted_at = datetime.utcnow()
    db.session.commit()
    return _success({"id": id})


@api_bp.post("/accounts/<int:id>/restore")
@login_required
def accounts_restore(id):
    a = _get_account(id, include_deleted=True)
    if a.deleted_at is None:
        return _success(_account_to_dict(a))
    dup = (
        Account.query.filter(Account.user_id == current_user.id)
        .filter(db.func.lower(Account.name) == a.name.lower())
        .filter(Account.deleted_at.is_(None))
        .first()
    )
    if dup:
        return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    a.deleted_at = None
    db.session.commit()
    return _success(_account_to_dict(a))


# --- Categories CRUD ---

def _category_to_dict(c: Category):
    return {"id": c.id, "name": c.name, "kind": c.kind, "color": c.color}


@api_bp.get("/categories")
@login_required
def categories_list():
    items = (
        Category.query.filter_by(user_id=current_user.id)
        .filter(Category.deleted_at.is_(None))
        .all()
    )
    return _success([_category_to_dict(c) for c in items])


@api_bp.post("/categories")
@login_required
def categories_create():
    data = request.get_json() or {}
    name = data.get("name")
    kind = data.get("kind")
    color = data.get("color", "#888888")
    if not name or not kind:
        return _error("name and kind required")
    exists = (
        Category.query.filter(Category.user_id == current_user.id)
        .filter(db.func.lower(Category.name) == name.lower())
        .filter(Category.deleted_at.is_(None))
        .first()
    )
    if exists:
        return _error("duplicate category name", status=409, errors={"name": ["exists"]})
    c = Category(user_id=current_user.id, name=name, kind=kind, color=color)
    db.session.add(c); db.session.commit()
    return _success(_category_to_dict(c), status=201)


def _get_category(id: int, include_deleted=False):
    q = Category.query.filter_by(id=id, user_id=current_user.id)
    if not include_deleted:
        q = q.filter(Category.deleted_at.is_(None))
    return q.first_or_404()


@api_bp.get("/categories/<int:id>")
@login_required
def categories_get(id):
    c = _get_category(id)
    return _success(_category_to_dict(c))


@api_bp.put("/categories/<int:id>")
@login_required
def categories_update(id):
    c = _get_category(id)
    data = request.get_json() or {}
    if "name" in data:
        name = data["name"]
        exists = (
            Category.query.filter(Category.user_id == current_user.id)
            .filter(db.func.lower(Category.name) == name.lower())
            .filter(Category.id != id)
            .filter(Category.deleted_at.is_(None))
            .first()
        )
        if exists:
            return _error("duplicate category name", status=409, errors={"name": ["exists"]})
    for field in ["name", "kind", "color"]:
        if field in data:
            setattr(c, field, data[field])
    db.session.commit()
    return _success(_category_to_dict(c))


@api_bp.delete("/categories/<int:id>")
@login_required
def categories_delete(id):
    c = _get_category(id)
    c.deleted_at = datetime.utcnow()
    db.session.commit()
    return _success({"id": id})


@api_bp.post("/categories/<int:id>/restore")
@login_required
def categories_restore(id):
    c = _get_category(id, include_deleted=True)
    if c.deleted_at is None:
        return _success(_category_to_dict(c))
    dup = (
        Category.query.filter(Category.user_id == current_user.id)
        .filter(db.func.lower(Category.name) == c.name.lower())
        .filter(Category.deleted_at.is_(None))
        .first()
    )
    if dup:
        return _error("duplicate category name", status=409, errors={"name": ["exists"]})
    c.deleted_at = None
    db.session.commit()
    return _success(_category_to_dict(c))


# --- Rules CRUD ---

def _rule_to_dict(r: Rule):
    def _safe(v):
        return None if isinstance(v, type) else v
    return {
        "id": r.id,
        "pattern": r.pattern,
        "field": r.field,
        "category_id": r.category_id,
        "min_amount": _safe(getattr(r, "min_amount", None)),
        "max_amount": _safe(getattr(r, "max_amount", None)),
        "priority": r.priority,
        "active": r.active,
    }


@api_bp.get("/rules")
@login_required
def rules_list():
    items = (
        Rule.query.filter_by(user_id=current_user.id)
        .filter(Rule.deleted_at.is_(None))
        .all()
    )
    return _success([_rule_to_dict(r) for r in items])


@api_bp.post("/rules")
@login_required
def rules_create():
    data = request.get_json() or {}
    pattern = data.get("pattern")
    field = data.get("field", "merchant")
    category_id = data.get("category_id")
    min_amount = data.get("min_amount")
    max_amount = data.get("max_amount")
    priority = data.get("priority", 100)
    active = data.get("active", True)
    if not pattern:
        return _error("pattern required")
    if category_id:
        cat = (
            Category.query.filter_by(id=category_id, user_id=current_user.id)
            .filter(Category.deleted_at.is_(None))
            .first()
        )
        if not cat:
            return _error("invalid category")
    r = Rule(
        user_id=current_user.id,
        pattern=pattern,
        field=field,
        category_id=category_id,
        min_amount=min_amount,
        max_amount=max_amount,
        priority=priority,
        active=active,
    )
    db.session.add(r); db.session.commit()
    return _success(_rule_to_dict(r), status=201)


def _get_rule(id: int, include_deleted=False):
    q = Rule.query.filter_by(id=id, user_id=current_user.id)
    if not include_deleted:
        q = q.filter(Rule.deleted_at.is_(None))
    return q.first_or_404()


@api_bp.get("/rules/<int:id>")
@login_required
def rules_get(id):
    r = _get_rule(id)
    return _success(_rule_to_dict(r))


@api_bp.put("/rules/<int:id>")
@login_required
def rules_update(id):
    r = _get_rule(id)
    data = request.get_json() or {}
    for field in ["pattern", "field", "category_id", "min_amount", "max_amount", "priority", "active"]:
        if field in data:
            setattr(r, field, data[field])
    db.session.commit()
    return _success(_rule_to_dict(r))


@api_bp.delete("/rules/<int:id>")
@login_required
def rules_delete(id):
    r = _get_rule(id)
    r.deleted_at = datetime.utcnow()
    db.session.commit()
    return _success({"id": id})


@api_bp.post("/rules/<int:id>/restore")
@login_required
def rules_restore(id):
    r = _get_rule(id, include_deleted=True)
    if r.deleted_at is None:
        return _success(_rule_to_dict(r))
    r.deleted_at = None
    db.session.commit()
    return _success(_rule_to_dict(r))
