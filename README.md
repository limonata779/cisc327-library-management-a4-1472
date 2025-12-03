[![Tests](https://github.com/limonata779/cisc327-library-management-a2--1472/actions/workflows/python-tests.yml/badge.svg)](https://github.com/limonata779/cisc327-library-management-a2--1472/actions/workflows/python-tests.yml)

A small library app used for CISC/CMPE 327. It keeps a catalog, lets patrons borrow/return books, calculates late fees, and exposes simple pages/APIs. The code is written to be easy to unit test.
# Python 3.10+ recommended (3.11 used in CI)

python -m venv .venv
source .venv/bin/activate
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# 2) install deps
pip install -r requirements.txt

# 3) init the SQLite DB
python -c "from database import init_database, add_sample_data; init_database(); add_sample_data()"

# 4) run the app
flask --app app.py run

# 5) run tests
pytest -q
# or just the suite:
pytest -q tests/


