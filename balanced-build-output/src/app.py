#!/usr/bin/env python3
"""
Main entry point for the backend application.

Handles routing and initialization of core services.
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Import and register blueprints
from .routes import main_bp
app.register_blueprint(main_bp)

# Initialize core services
from .services import init_services
init_services(app)

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)