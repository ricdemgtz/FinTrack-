from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, hashlib
from datetime import date
from .. import db
from ..models import Transaction, Attachment, Account
from ..ocr import extract_fields

api_bp = Blueprint("api", __name__)

def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())

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
