# FinTrack+ (Scaffold)

This is the starter scaffold for **FinTrack+**, your CS50 final project.
It includes a minimal Flask app with blueprints, models, templates, and a basic UI.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Then open http://localhost:5000

## Structure

```
fintrack/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── ocr.py
│   ├── classify.py
│   ├── auth/
│   │   └── routes.py
│   ├── api/
│   │   └── routes.py
│   ├── web/
│   │   └── routes.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── transactions/
│   │   │   └── list.html
│   │   └── rules/
│   │       └── list.html
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   └── js/
│   │       └── main.js
│   └── uploads/  # created at runtime
├── migrations/   # reserved for Flask-Migrate
├── tests/
│   └── test_sanity.py
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## Notes

- OCR and PDF export are stubbed with safe defaults; you'll implement them incrementally.
- The DB defaults to SQLite for easy local dev; you can switch to MySQL/Postgres by setting `DATABASE_URL` in `.env`.
- Make sure `tesseract-ocr` is installed on your OS if you use OCR.
