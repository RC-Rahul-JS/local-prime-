from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    print(f"🚀 Starting Local Prime Enterprise Server on port {Config.PORT}...")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
