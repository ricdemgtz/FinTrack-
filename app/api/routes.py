from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, hashlib
from datetime import date, datetime
from .. import db
from ..models import Transaction, Attachment, Account, Category, Rule
from ..ocr import extract_fields
from sqlalchemy.exc import IntegrityError

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


def _supports_partial_index():
    bind = db.session.get_bind()
    return bind.dialect.name == "postgresql"

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
    return {
        "id": a.id,
        "name": a.name,
        "type": a.type,
        "currency": a.currency,
        "opening_balance": float(a.opening_balance),
        "active": a.active,
    }


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
    opening_balance = data.get("opening_balance", 0)
    active = data.get("active", True)
    if not name or not (1 <= len(name) <= 80):
        return _error("invalid name", errors={"name": ["required or length"]})
    if not acc_type:
        return _error("name and type required")
    if acc_type not in current_app.config.get("ALLOWED_ACCOUNT_TYPES", set()):
        return _error(
            "invalid account type",
            status=422,
            errors={"type": ["invalid"]},
        )
    if currency not in current_app.config.get("ALLOWED_CURRENCIES", []):
        return _error(
            "invalid currency",
            status=422,
            errors={"currency": ["invalid"]},
        )
    try:
        opening_balance = float(opening_balance)
    except (TypeError, ValueError):
        return _error(
            "invalid opening_balance",
            status=422,
            errors={"opening_balance": ["invalid"]},
        )
    if opening_balance < 0:
        return _error(
            "opening_balance must be >= 0",
            status=422,
            errors={"opening_balance": ["negative"]},
        )
    if not isinstance(active, bool):
        return _error(
            "invalid active",
            status=422,
            errors={"active": ["invalid"]},
        )
    supports_partial = _supports_partial_index()
    if not supports_partial:
        exists = (
            Account.query.filter(Account.user_id == current_user.id)
            .filter(db.func.lower(Account.name) == name.lower())
            .filter(Account.deleted_at.is_(None))
            .first()
        )
        if exists:
            return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    a = Account(
        user_id=current_user.id,
        name=name,
        type=acc_type,
        currency=currency,
        opening_balance=opening_balance,
        active=active,
    )
    db.session.add(a)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate account name", status=409, errors={"name": ["exists"]})
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
        supports_partial = _supports_partial_index()
        if not supports_partial:
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
    if "type" in data:
        if data["type"] not in current_app.config.get("ALLOWED_ACCOUNT_TYPES", set()):
            return _error(
                "invalid account type",
                status=422,
                errors={"type": ["invalid"]},
            )
        a.type = data["type"]
    if "currency" in data:
        if data["currency"] not in current_app.config.get("ALLOWED_CURRENCIES", []):
            return _error(
                "invalid currency",
                status=422,
                errors={"currency": ["invalid"]},
            )
        a.currency = data["currency"]
    if "opening_balance" in data:
        try:
            ob = float(data["opening_balance"])
        except (TypeError, ValueError):
            return _error(
                "invalid opening_balance",
                status=422,
                errors={"opening_balance": ["invalid"]},
            )
        if ob < 0:
            return _error(
                "opening_balance must be >= 0",
                status=422,
                errors={"opening_balance": ["negative"]},
            )
        a.opening_balance = ob
    if "active" in data:
        if not isinstance(data["active"], bool):
            return _error(
                "invalid active",
                status=422,
                errors={"active": ["invalid"]},
            )
        a.active = data["active"]
    if "name" in data:
        a.name = data["name"]
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    return _success(_account_to_dict(a))


@api_bp.delete("/accounts/<int:id>")
@login_required
def accounts_delete(id):
    a = _get_account(id)
    rules = (
        Rule.query.filter_by(user_id=current_user.id, scope_account_id=id, active=True)
        .filter(Rule.deleted_at.is_(None))
        .all()
    )
    for r in rules:
        r.active = False
    a.deleted_at = datetime.utcnow()
    db.session.commit()
    count = len(rules)
    return _success({"id": id, "disabled_rules": count}, message=f"{count} rule(s) disabled")


@api_bp.post("/accounts/<int:id>/restore")
@login_required
def accounts_restore(id):
    a = _get_account(id, include_deleted=True)
    if a.deleted_at is None:
        return _success(_account_to_dict(a))
    supports_partial = _supports_partial_index()
    if not supports_partial:
        dup = (
            Account.query.filter(Account.user_id == current_user.id)
            .filter(db.func.lower(Account.name) == a.name.lower())
            .filter(Account.deleted_at.is_(None))
            .first()
        )
        if dup:
            return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    data = request.get_json() or {}
    a.deleted_at = None
    if data.get("active") is True:
        a.active = True
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate account name", status=409, errors={"name": ["exists"]})
    return _success(_account_to_dict(a))


# --- Categories CRUD ---

def _category_to_dict(c: Category):
    return {
        "id": c.id,
        "name": c.name,
        "kind": c.kind,
        "color": c.color,
        "icon_emoji": c.icon_emoji,
        "parent_id": c.parent_id,
        "is_system": c.is_system,
    }


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
    name = (data.get("name") or "").strip()
    kind = data.get("kind")
    color = data.get("color", "#888888")
    icon_emoji = data.get("icon_emoji")
    parent_id = data.get("parent_id")
    is_system = data.get("is_system", False)
    if not name or not (1 <= len(name) <= 60):
        return _error("invalid name", errors={"name": ["required or length"]})
    if not kind:
        return _error("name and kind required")
    supports_partial = _supports_partial_index()
    if not supports_partial:
        exists = (
            Category.query.filter(Category.user_id == current_user.id)
            .filter(db.func.lower(Category.name) == name.lower())
            .filter(Category.deleted_at.is_(None))
            .first()
        )
        if exists:
            return _error("duplicate category name", status=409, errors={"name": ["exists"]})
    c = Category(
        user_id=current_user.id,
        name=name,
        kind=kind,
        color=color,
        icon_emoji=icon_emoji,
        parent_id=parent_id,
        is_system=is_system,
    )
    db.session.add(c)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate category name", status=409, errors={"name": ["exists"]})
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
        name = (data["name"] or "").strip()
        if not name or not (1 <= len(name) <= 60):
            return _error("invalid name", errors={"name": ["required or length"]})
        supports_partial = _supports_partial_index()
        if not supports_partial:
            exists = (
                Category.query.filter(Category.user_id == current_user.id)
                .filter(db.func.lower(Category.name) == name.lower())
                .filter(Category.id != id)
                .filter(Category.deleted_at.is_(None))
                .first()
            )
            if exists:
                return _error("duplicate category name", status=409, errors={"name": ["exists"]})
        data["name"] = name
    for field in ["name", "kind", "color", "icon_emoji", "parent_id", "is_system"]:
        if field in data:
            setattr(c, field, data[field])
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate category name", status=409, errors={"name": ["exists"]})
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
    supports_partial = _supports_partial_index()
    if not supports_partial:
        dup = (
            Category.query.filter(Category.user_id == current_user.id)
            .filter(db.func.lower(Category.name) == c.name.lower())
            .filter(Category.deleted_at.is_(None))
            .first()
        )
        if dup:
            return _error("duplicate category name", status=409, errors={"name": ["exists"]})
    c.deleted_at = None
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("duplicate category name", status=409, errors={"name": ["exists"]})
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
        "scope_account_id": r.scope_account_id,
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
    scope_account_id = data.get("scope_account_id")
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
    if scope_account_id:
        acc = (
            Account.query.filter_by(id=scope_account_id, user_id=current_user.id)
            .filter(Account.deleted_at.is_(None))
            .first()
        )
        if not acc:
            return _error("invalid account")
    r = Rule(
        user_id=current_user.id,
        pattern=pattern,
        field=field,
        category_id=category_id,
        scope_account_id=scope_account_id,
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
    for field in [
        "pattern",
        "field",
        "category_id",
        "scope_account_id",
        "min_amount",
        "max_amount",
        "priority",
        "active",
    ]:
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
