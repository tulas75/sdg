"""Main Flask application entry point."""
import os
from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration from .env file
    app.config.from_prefixed_env()
    
    # Register blueprints
    from app.api.routes import bp as api_bp
    app.register_blueprint(api_bp)
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)