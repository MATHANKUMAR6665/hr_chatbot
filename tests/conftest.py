import pytest
from seed_database import seed
from app import dialogue_manager


@pytest.fixture(scope="session", autouse=True)
def fresh_database():
    seed()                       # reset demo data once per test run


@pytest.fixture(autouse=True)
def clean_sessions():
    dialogue_manager.reset_all_sessions()   # every test starts a new conversation
