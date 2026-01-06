# api/index.py
from app import app

# This is needed for Vercel serverless functions
if __name__ == "__main__":
    app.run()