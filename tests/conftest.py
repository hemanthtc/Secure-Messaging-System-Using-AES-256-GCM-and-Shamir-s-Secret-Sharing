"""
Pytest Configuration and Fixtures
Sets up isolated test environment using mongomock for fast, reliable, offline testing.
"""

import pytest
from app import create_app
from app.database.db import mongo
from app.database.schema import reset_db
from app.services.auth_service import AuthService
from app.security.rate_limiting import clear_rate_limits

@pytest.fixture(scope="session")
def app():
    """Create test application instance configured with TestingConfig."""
    app_instance = create_app("testing")
    return app_instance

@pytest.fixture(autouse=True)
def clean_db(app):
    """Automatically clear mongomock database collections and rate limits before each test."""
    with app.app_context():
        reset_db(app)
        clear_rate_limits()
    yield
    with app.app_context():
        reset_db(app)
        clear_rate_limits()

@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def registered_user(app):
    """Fixture providing a standard registered user."""
    with app.app_context():
        user, _ = AuthService.register_user(
            display_name="Hemanth Kumar",
            public_user_id="hemanth_101",
            password="SecurePassword123!"
        )
        return user

@pytest.fixture
def second_user(app):
    """Fixture providing a second registered user for chat interactions."""
    with app.app_context():
        user, _ = AuthService.register_user(
            display_name="Ananya Sharma",
            public_user_id="ananya_202",
            password="AnotherSecurePassword123!"
        )
        return user
