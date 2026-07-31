import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base Configuration Class."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key")
    MONGO_URI = os.getenv("MONGO_URI", "")
    PORT = int(os.getenv("PORT", 5001))
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"

    @staticmethod
    def validate():
        """Ensure critical configuration variables are set."""
        if not Config.MONGO_URI:
            raise ValueError("CRITICAL: MONGO_URI is not configured in .env file.")
