"""
SecureShare Messenger - Configuration Module
Defines settings for Development, Testing, and Production environments
with MongoDB Atlas database integration.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def load_env_file():
    """Load key-value pairs from .env file into os.environ if present."""
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

load_env_file()

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "secureshare-messenger-academic-dev-key-2026")
    
    # MongoDB Atlas Database Settings (supports both MONGO_URI and MONGODB_URI)
    MONGO_URI = (
        os.environ.get("MONGO_URI")
        or os.environ.get("MONGODB_URI")
        or "mongodb://localhost:27017/secureshare"
    )
    MONGO_DB_NAME = (
        os.environ.get("MONGO_DB_NAME")
        or os.environ.get("MONGODB_DB_NAME")
        or "secureshare"
    )
    USE_MONGOMOCK = False
    
    # Message & Fragmentation Constraints
    MIN_FRAGMENTS = 2
    MAX_FRAGMENTS = 10
    DEFAULT_FRAGMENTS = 3
    MAX_MESSAGE_PAYLOAD_BYTES = 65536  # 64 KB input size limit per message
    
    # Shamir Secret Sharing Constraints
    MIN_SSS_SHARES = 2
    MAX_SSS_SHARES = 10
    
    # Security & Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable static asset caching to ensure cross-browser consistency
    
    # Argon2 Parameters
    ARGON2_TIME_COST = 2
    ARGON2_MEMORY_COST = 65536  # 64 MB
    ARGON2_PARALLELISM = 2
    ARGON2_HASH_LEN = 32
    ARGON2_SALT_LEN = 16


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    SEND_FILE_MAX_AGE_DEFAULT = 0


class TestingConfig(Config):
    """Testing environment configuration using mongomock for fast, isolated tests."""
    DEBUG = False
    TESTING = True
    USE_MONGOMOCK = True
    MONGO_DB_NAME = "secureshare_test"
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration with strict MongoDB Atlas requirement."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
