import os
import tempfile
import pytest

# Ensure tests run against an isolated test database
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
test_db_path = test_db_file.name
test_db_file.close()

os.environ["DB_PATH"] = test_db_path

# Re-import config to make sure DB_PATH is updated
from app.core import config
config.DB_PATH = config.Path(test_db_path)

from app.database.schema import init_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_database()
    yield
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass
