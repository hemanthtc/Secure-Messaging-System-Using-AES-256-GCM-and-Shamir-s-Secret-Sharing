"""
Database Initialization Script for MongoDB Atlas
Ensures collections and unique indexes are created properly in MongoDB Atlas.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.database.schema import init_db

if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    with app.app_context():
        print("[*] Initializing MongoDB Atlas indexes and collections...")
        init_db(app)
        print("[+] MongoDB Atlas initialization completed successfully.")
