import sys
from pathlib import Path
import pytest

# Make imports work no matter where pytest is started from
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# imported after fixing sys.path
import database

@pytest.fixture(autouse=True)
def sandbox_db(tmp_path, monkeypatch):
    """
    For every test point the app at a throwaway sqlite file and build the tables.
    """
    db_file = tmp_path / "sqlite_test.db"
    monkeypatch.setattr(database, "DATABASE", str(db_file), raising=False)
    database.init_database()

    # sanity check to check tests are using the temp DB
    assert str(database.DATABASE).endswith("sqlite_test.db")

    # tmp_path is cleaned by pytest
    yield
