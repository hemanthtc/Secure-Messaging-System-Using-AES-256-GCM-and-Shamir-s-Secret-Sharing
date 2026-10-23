"""
Server Runner Script
Runs the SecureShare Messenger application.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, socketio

if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    socketio.run(app, host=host, port=port, debug=(env == "development"), use_reloader=False, allow_unsafe_werkzeug=True)
