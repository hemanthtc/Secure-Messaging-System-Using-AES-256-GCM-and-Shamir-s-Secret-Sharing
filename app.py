"""
SecureShare Messenger - Application Entry Point
Starts the Flask-SocketIO development or production server.
"""

import os
from app import create_app, socketio

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = env == "development"
    print(f"[*] Starting SecureShare Messenger on http://{host}:{port} ({env} mode)")
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
