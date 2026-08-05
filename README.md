# Transaction Record App (Base)

Minimal web-based transaction record-keeping app implementing the SRS base features: owner/staff roles, authentication, transaction CRUD (owner), view-only for staff, daily report (CSV), and invoice generation.

Quick start

1. Create a Python virtualenv and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Initialize the database (seeds `owner`/`staff` test users):

```bash
python init_db.py
```

3. Run the app:

```bash
python app.py
```

Default seeded users: `owner` / `ownerpass` (role: owner), `staff` / `staffpass` (role: staff). Change passwords before production.

Note: If Python isn't available on your machine, install Python 3.9+ and then follow the steps above.
