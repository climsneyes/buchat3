import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "https://pychat-25c45-default-rtdb.asia-southeast1.firebasedatabase.app/")
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")
