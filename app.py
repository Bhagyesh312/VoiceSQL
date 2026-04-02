import sys
import os

# Add backend directory to path so imports work
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "backend"))

# Set working context so relative paths inside backend work
os.chdir(os.path.join(BASE, "backend"))

from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
