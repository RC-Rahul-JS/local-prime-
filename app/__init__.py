from flask import Flask, jsonify
from app.config import Config
from app.routes.loan_routes import loan_bp
from app.routes.payment_routes import payment_bp
from app.routes.interest_routes import interest_bp
from app.routes.invoice_routes import invoice_bp

def create_app(config_class=Config):
    """Application factory for creating and configuring the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Blueprints
    app.register_blueprint(loan_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(interest_bp)
    app.register_blueprint(invoice_bp)

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "local-prime API",
            "version": "1.0.0"
        }), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource or endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app
