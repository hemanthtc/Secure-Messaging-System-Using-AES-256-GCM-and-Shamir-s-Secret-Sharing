"""
Authentication Automated Unit and Integration Tests
Tests registration, login (3 factors), duplicate ID rejection, and logout.
"""

from app.models.user import User

def test_registration_success(client):
    """Test successful user registration with Name, User ID, and Password."""
    res = client.post("/signup", data={
        "display_name": "Test User",
        "public_user_id": "test_user_1",
        "password": "Password1234!"
    }, follow_redirects=True)
    assert res.status_code == 200

    user = User.find_by_public_id("test_user_1")
    assert user is not None
    assert user.display_name == "Test User"
    assert user.password_hash.startswith("$argon2") or user.password_hash.startswith("scrypt$")

def test_duplicate_public_user_id_rejected(client, registered_user):
    """Test that attempting to register an existing public user ID is rejected."""
    res = client.post("/signup", data={
        "display_name": "Imposter Hemanth",
        "public_user_id": "hemanth_101",
        "password": "Password1234!"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"already taken" in res.data

def test_login_success(client, registered_user):
    """Test successful login requiring all 3: Name, User ID, and Password."""
    res = client.post("/login", data={
        "display_name": "Hemanth Kumar",
        "public_user_id": "hemanth_101",
        "password": "SecurePassword123!"
    }, follow_redirects=True)
    assert res.status_code == 200

    # Verify session established
    with client.session_transaction() as sess:
        assert sess.get("user_internal_id") == registered_user.internal_id

def test_login_invalid_password_rejected(client, registered_user):
    """Test login rejection when password is incorrect."""
    res = client.post("/login", data={
        "display_name": "Hemanth Kumar",
        "public_user_id": "hemanth_101",
        "password": "WrongPassword123!"
    }, follow_redirects=True)
    assert b"Invalid credentials" in res.data

def test_login_mismatched_name_rejected(client, registered_user):
    """Test login rejection when supplied name does not match the account."""
    res = client.post("/login", data={
        "display_name": "Wrong Name",
        "public_user_id": "hemanth_101",
        "password": "SecurePassword123!"
    }, follow_redirects=True)
    assert b"Invalid credentials" in res.data

def test_logout_clears_session(client, registered_user):
    """Test that logout invalidates the authenticated session."""
    client.post("/login", data={
        "display_name": "Hemanth Kumar",
        "public_user_id": "hemanth_101",
        "password": "SecurePassword123!"
    })
    res = client.get("/logout", follow_redirects=True)
    assert res.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get("user_internal_id") is None
