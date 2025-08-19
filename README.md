# FinTrack+ (Scaffold)

This is the starter scaffold for **FinTrack+**, your CS50 final project.
It includes a minimal Flask app with blueprints, models, templates, and a basic UI.

## Quickstart

Interactively explore the basic setup using the expandable sections below.

<details>
<summary><strong>📦 Environment setup</strong></summary>

1. Create and activate a virtual environment

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```

2. Install dependencies

    ```bash
    pip install -r requirements.txt
    ```

3. Configure environment variables

    ```bash
    cp .env.example .env
    ```

</details>

<details>
<summary><strong>🚀 Run the app</strong></summary>

```bash
python run.py
```

Then open http://localhost:5000 in your browser.

</details>

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
