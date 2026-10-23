"""
SecureShare Messenger Application Factory
Initializes Flask app, MongoDB Atlas connection, SocketIO, and blueprint routing.
"""

import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from config import config_by_name
from app.database.db import mongo
from app.realtime.socket_events import register_socket_events

# Singleton SocketIO instance
socketio = SocketIO(cors_allowed_origins="*", async_mode=None)

def create_app(config_name="development"):
    """Flask application factory."""
    base_dir = os.path.dirname(__file__)
    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )
    
    # Load configuration
    cfg = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg)

    # Initialize MongoDB Atlas database connection
    mongo.init_app(app)

    # Initialize Flask-SocketIO
    socketio.init_app(app)
    register_socket_events(socketio)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.user_routes import user_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.message_routes import message_bp
    from app.routes.settings_routes import settings_bp
    from app.routes.share_link_routes import share_link_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(share_link_bp)

    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error.html", error_message="Page or resource not found (404)."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("error.html", error_message="Internal server error (500)."), 500

    @app.after_request
    def set_cache_control_headers(response):
        """Ensure fresh assets across all browsers by preventing stale caching."""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app
