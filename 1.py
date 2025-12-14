import os
from dotenv import load_dotenv
load_dotenv()
print("FLASK_ENV=", os.getenv("FLASK_ENV"))
print("ALLOWED_ORIGINS=", os.getenv("ALLOWED_ORIGINS"))
print("CORS_CREDENTIALS=", os.getenv("CORS_CREDENTIALS"))